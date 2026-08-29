"""Bokföringsagentens endpoints.

## Vad agenten ALDRIG får göra härifrån

Den skickar ingenting till Skatteverket eller Bolagsverket, och den flyttar
inga pengar. Det finns ingen sådan endpoint och inget verktyg som når en. Allt
den producerar är förslag en människa godkänner — samma gräns som
`send_guard` drar för leads-agenten, fast här behöver den inte dras i kod
eftersom vägen ut inte finns.

## Periodrapporten kan inte visas som klar utan grinden

`GET /api/bookkeeping/period` returnerar ALLTID ett `status`-fält. Det finns
ingen kodväg som ger summor utan att `check_period` körts på underlaget de
räknats ur, och en fälld period levererar sina brister i stället för att
avrunda bort dem.
"""

from __future__ import annotations

import json as _json
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from fastapi import File as FastAPIFile

from ..agent.bookkeeping_agent import (
    AGENT_TYPE,
    FORBEHALL,
    las_underlag,
    run_bookkeeping_chat_turn,
)
from ..agentcore.overlays import pack_version
from ..bookkeeping.kontoutdrag import KontoutdragsfelError, las_kontoutdrag, stam_av
from ..bookkeeping.math import Konteringsrad
from ..bookkeeping.period import berakna_period, kr
from ..bookkeeping.sie4 import SieExportError, Verifikat, skriv_sie4
from ..bookkeeping.underlag import (
    UnderlagsfelError,
    kontrollera_fil,
    las_bild_text,
    las_pdf_text,
    sha256_av,
)
from ..bookkeeping.verifieringsgrind import STATUS_GRANSKA, STATUS_KLAR
from ..config import get_settings
from .deps import require_tenant

router = APIRouter()

def _underlag_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {
        **{k: v for k, v in rad.items() if k not in ("brutto", "momssats", "tenant_id")},
        "brutto": kr(rad.get("brutto")),
        "momssats": kr(rad.get("momssats")),
    }


async def ta_emot_underlag(
    storage: Any, tenant_id: str, data: bytes, mimetyp: str, filnamn: str
) -> dict[str, Any]:
    """Kvittot in: kontrollera, läs av, spara fälten — och kasta filen.

    ## Varför den är en egen funktion och inte en endpoint-kropp

    Underlag kommer in på TVÅ vägar: uppladdningspanelen (`POST
    /api/bookkeeping/underlag`) och ett kvitto som droppas i chatten (`POST
    /api/bookkeeping/chat`). Bägge måste gå exakt samma väg — samma
    filkontroll, samma textutvinning, samma `las_underlag`, samma verifikat.

    En andra läsväg hade sett identisk ut den dag den skrevs och glidit isär vid
    första ändringen: ett höjt filtak på ena stället, en ny mimetyp på andra,
    och plötsligt beror avläsningens kvalitet på VAR kunden råkade släppa
    filen. `tests/test_bokforing_chatt.py` fäller om chatten slutar gå genom
    den här funktionen.

    Ordningen är hela poängen: filen finns bara i minnet under anropet, och det
    som skrivs till databasen är fälten plus en sha256. Se
    `app/bookkeeping/underlag.py`.

    ## Dubblettspärren

    Samma fil två gånger är nästan alltid ett misstag — en dubbelklick, ett
    kvitto någon glömt att de redan laddat upp — och ett dubblerat underlag
    blir en dubblerad kostnad i periodrapporten, vilket är precis den sortens
    trovärdiga men felaktiga tal INV-BOOK-002 finns för att stoppa. Spärren
    jämför sha256 mot tenantens befintliga underlag (det är hela skälet till
    att hashen sparas, se storage/base.py) och avvisar med 422 i stället för
    att tyst spara en flaggad rad: ett tydligt nej vid uppladdningen är
    billigare än en granskningspost, och kostar dessutom inget LLM-anrop —
    därför ligger den FÖRE textutvinningen. Två identiska köp ger aldrig två
    byteidentiska filer (foton skiljer sig alltid), så falsklarmsrisken som
    fällde dubblettdetektering i verifieringsgrinden finns inte här.
    """
    kontrollera_fil(data, mimetyp)

    sha256 = sha256_av(data)
    settings = get_settings()
    dubblett = await storage.get_bk_underlag_by_sha256(tenant_id, sha256)
    if dubblett is not None:
        beskrivning = dubblett.get("filnamn") or "ett underlag"
        datum = dubblett.get("datum")
        raise UnderlagsfelError(
            f"Samma fil är redan uppladdad ({beskrivning}"
            + (f", {datum}" if datum else "")
            + "). Dubbletten sparades inte — radera den gamla först om den är fel."
        )

    if mimetyp == "application/pdf":
        text = las_pdf_text(data)
        if not text:
            # En skannad PDF saknar textlager. Det är ett svar, inte ett fel —
            # och att säga vad kunden ska göra i stället är billigare än att
            # låta grinden fälla på "allt saknas".
            raise UnderlagsfelError(
                "PDF:en saknar textlager (troligen en skanning). Ladda upp "
                "den som bild i stället, så läses den av bildvägen."
            )
    else:
        import base64

        data_url = f"data:{mimetyp};base64,{base64.b64encode(data).decode()}"
        text = await las_bild_text(data_url)

    avlasning = await las_underlag(text)

    underlag = await storage.create_bk_underlag(
        tenant_id,
        sha256=sha256,
        filnamn=filnamn or "underlag",
        mimetyp=mimetyp,
        status=avlasning.status,
        anmarkning=avlasning.anmarkning or "; ".join(avlasning.verdikt.as_report()),
        **{
            k: v
            for k, v in avlasning.falt.items()
            if k in ("datum", "motpart", "brutto", "momssats", "riktning", "kategori")
        },
    )

    if avlasning.verifikat:
        # Verifikatnumret räknas ur antalet befintliga verifikat, inte ur en
        # räknarkolumn: en räknare kan glida isär med verkligheten, och ett
        # hoppat verifikatnummer är en anmärkning vid revision.
        befintliga = await storage.list_bk_verifikat(tenant_id)
        await storage.create_bk_verifikat(
            tenant_id,
            underlag_id=underlag["id"],
            serie="A",
            nummer=str(len(befintliga) + 1),
            datum=avlasning.falt["datum"],
            text=avlasning.falt.get("motpart", ""),
            rader=[
                {"konto": r.konto, "debet": r.debet, "kredit": r.kredit, "text": r.text}
                for r in avlasning.verifikat
            ],
        )

    await storage.log_agent_run(
        tenant_id,
        agent_type=AGENT_TYPE,
        pack_version=pack_version("bokforing/v1"),
        skills_used=avlasning.trace.skills_used,
        input_text=text[:4000],
        output_text=str(avlasning.falt),
        step_log=avlasning.trace.as_log(),
        tokens_in=avlasning.trace.total_tokens_in,
        tokens_out=avlasning.trace.total_tokens_out,
        latency_ms=sum(s.latency_ms for s in avlasning.trace.steps),
        model=f"{settings.llm_provider}:{settings.model}",
    )

    return {
        "underlag": _underlag_ut(underlag),
        "status": avlasning.status,
        "brister": avlasning.verdikt.as_report(),
        # Ett utdrag ur den AVLÄSTA texten, inte ur filen. Chatten använder det
        # så att assistenten kan svara på vad som STOD på underlaget och inte
        # bara på de sex fält avläsningen plockar ut.
        #
        # Taket är inte kosmetik: hela texten från en flersidig faktura äter
        # kontextfönstret, och den gör dessutom INV-BOOK-003 mer generös än den
        # ska vara — varje tal i utdraget blir ett grundat tal.
        "text": text[:2000],
    }


@router.post("/api/bookkeeping/underlag")
async def ladda_upp_underlag(
    request: Request,
    fil: UploadFile = FastAPIFile(...),
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Uppladdningspanelens väg in. Arbetet görs av `ta_emot_underlag`."""
    try:
        resultat = await ta_emot_underlag(
            request.app.state.storage,
            tenant["tenant_id"],
            await fil.read(),
            fil.content_type or "",
            fil.filename or "underlag",
        )
    except UnderlagsfelError as fel:
        raise HTTPException(status_code=422, detail=str(fel)) from fel

    # Texten går INTE vidare till uppladdningspanelen. Den behövs bara av
    # chatten, och ett svar som bär hela kvittots innehåll till en vy som visar
    # fält är innehåll som skickas utan att användas.
    return {**{k: v for k, v in resultat.items() if k != "text"}, "forbehall": FORBEHALL}


@router.get("/api/bookkeeping/underlag")
async def lista_underlag(
    request: Request,
    fran: date | None = None,
    till: date | None = None,
    tenant: dict = Depends(require_tenant),
) -> dict:
    rader = await request.app.state.storage.list_bk_underlag(
        tenant["tenant_id"], fran=fran, till=till
    )
    return {"underlag": [_underlag_ut(r) for r in rader], "forbehall": FORBEHALL}


@router.get("/api/bookkeeping/period")
async def periodrapport(
    request: Request,
    fran: date,
    till: date,
    tenant: dict = Depends(require_tenant),
) -> dict:
    rapport = await berakna_period(request.app.state.storage, tenant["tenant_id"], fran, till)
    rapport.pop("_verifikat", None)
    return rapport


@router.delete("/api/bookkeeping/period")
async def rensa_period(
    request: Request,
    fran: date,
    till: date,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Tömmer perioden: underlagen och verifikaten som räknats ur dem.

    Det är den enda vägen tillbaka från ett felläst underlag. Rättelsevägen
    (`update_bk_underlag`) förutsätter att man vet vad som skulle stått; den
    här förutsätter bara att man vill börja om.

    RADERINGEN ÄR ÄKTA, inte en flagga. Originalfilerna finns inte att radera
    — bara `sha256` sparades någonsin — så det som försvinner är de utlästa
    fälten och konteringsförslagen. Att det INTE går att ångra är hela skälet
    till att vyn frågar först.

    Urvalet är samma som `lista_underlag` visar, `datum is null` inräknat. Se
    `rensa_bk_period` i app/storage/base.py för varför.
    """
    antal = await request.app.state.storage.rensa_bk_period(
        tenant["tenant_id"], fran=fran, till=till
    )
    return {"raderade": antal}


@router.get("/api/bookkeeping/period.sie")
async def exportera_sie4(
    request: Request,
    fran: date,
    till: date,
    foretagsnamn: str,
    orgnr: str,
    tenant: dict = Depends(require_tenant),
) -> Response:
    """SIE4-filen kundens eget bokföringsprogram importerar.

    En FÄLLD period exporteras inte. Mottagarsystemet hade avvisat filen ändå,
    men då på kundens skärm i deras program — och det är för sent.
    """
    rapport = await berakna_period(request.app.state.storage, tenant["tenant_id"], fran, till)
    if rapport["status"] != STATUS_KLAR:
        raise HTTPException(
            status_code=409,
            detail={
                "fel": "Perioden går inte ihop och kan inte exporteras.",
                "status": STATUS_GRANSKA,
                "brister": rapport["brister"],
            },
        )

    try:
        data = skriv_sie4(
            foretagsnamn=foretagsnamn,
            orgnr=orgnr,
            rakenskapsar_start=date(fran.year, 1, 1),
            rakenskapsar_slut=date(fran.year, 12, 31),
            genererat=till,
            verifikat=[
                Verifikat(
                    serie=v["serie"],
                    nummer=v["nummer"],
                    datum=date.fromisoformat(v["datum"]),
                    text=v["text"],
                    rader=tuple(
                        Konteringsrad(
                            konto=r["konto"],
                            debet=r["debet"],
                            kredit=r["kredit"],
                            text=r.get("text", ""),
                        )
                        for r in v["rader"]
                    ),
                )
                for v in rapport["_verifikat"]
            ],
        )
    except SieExportError as fel:
        raise HTTPException(status_code=409, detail=str(fel)) from fel

    return Response(
        content=data,
        # CP437, inte UTF-8. Deklarerad i både filen (#FORMAT PC8) och huvudet,
        # annars gissar mottagaren — se app/bookkeeping/sie4.py.
        media_type="application/octet-stream; charset=cp437",
        headers={
            "Content-Disposition": (
                f'attachment; filename="snajp-{fran.isoformat()}-{till.isoformat()}.se"'
            )
        },
    )


@router.post("/api/bookkeeping/chat")
async def chatt(
    request: Request,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Bokföringsassistenten. Ett meddelande in, ett svar ut.

    ## Varför den tar BÅDE JSON och multipart

    Ett kvitto som droppas i chatten ska bokföras som ett kvitto, inte som en
    bild i en chattlogg. Kroppen är därför multipart när en fil följer med och
    JSON annars, och filvägen är `ta_emot_underlag` — exakt samma funktion som
    uppladdningspanelen anropar. Se dess docstring om varför det inte får bli
    två läsvägar.

    ## Vad som INTE loggas

    `input_text` bär kundens fråga, `output_text` svaret. Filens innehåll når
    aldrig loggen: den läses i minnet av `ta_emot_underlag`, som skriver fälten
    och kastar bytesen.

    ## Vad som händer när beloppsgrinden fäller

    Svaret byts mot `FALLT_SVAR` innan det lämnar `run_bookkeeping_chat_turn`,
    och `grundad: false` följer med i JSON:en. Anropet är alltså inte ett fel —
    kunden får ett ärligt svar om att assistenten inte kunde härleda en siffra,
    och gränssnittet kan visa det som vad det är.
    """
    storage = request.app.state.storage
    settings = get_settings()
    typ = request.headers.get("content-type") or ""

    meddelande = ""
    historik: list[dict[str, Any]] = []
    bilaga: dict[str, Any] | None = None

    if typ.startswith("multipart/form-data"):
        form = await request.form()
        meddelande = str(form.get("meddelande") or "").strip()
        rå_historik = form.get("historik")
        if isinstance(rå_historik, str) and rå_historik:
            try:
                historik = _json.loads(rå_historik)
            except ValueError:
                historik = []

        fil = form.get("fil")
        if fil is not None and hasattr(fil, "read"):
            try:
                bilaga = await ta_emot_underlag(
                    storage,
                    tenant["tenant_id"],
                    await fil.read(),
                    getattr(fil, "content_type", "") or "",
                    getattr(fil, "filename", "") or "underlag",
                )
            except UnderlagsfelError as fel:
                raise HTTPException(status_code=422, detail=str(fel)) from fel
    else:
        kropp = await request.json()
        meddelande = str(kropp.get("meddelande") or "").strip()
        historik = kropp.get("historik") or []

    if not meddelande and bilaga is None:
        raise HTTPException(status_code=422, detail="Skriv en fråga eller bifoga ett underlag.")

    # Bilagan blir en del av FRÅGAN, inte ett separat svar. Kunden som släpper
    # ett kvitto utan att skriva något frågar i praktiken "vad blev det här?",
    # och assistenten ska svara på det utan att kunden behöver formulera det.
    forhamtat: list[str] = []
    if bilaga is not None:
        avläst = bilaga["underlag"]
        sammanfattning = (
            f"[Underlag mottaget: {avläst.get('filnamn')}. "
            f"Avläst datum {avläst.get('datum')}, motpart {avläst.get('motpart')}, "
            f"belopp {avläst.get('brutto')}, momssats {avläst.get('momssats')}, "
            f"kategori {avläst.get('kategori')}, status {bilaga['status']}."
            + (f" Brister: {'; '.join(bilaga['brister'])}." if bilaga["brister"] else "")
            + "]"
        )
        # TEXTEN från underlaget följer med, inte bara de sex avlästa fälten.
        #
        # Avläsningen plockar ut datum, motpart, belopp, momssats, riktning och
        # kategori. Allt annat som stod på kvittot — vad som köptes, antal
        # liter, ett fakturanummer — finns bara i texten. Utan den kan
        # assistenten inte svara på "vad köpte jag?", och en assistent som just
        # läst ett kvitto men inte kan säga vad som stod på det är svårare att
        # lita på än en som säger att den inte vet.
        meddelande = (
            f"{sammanfattning}\n\nText från underlaget:\n{bilaga.get('text', '')}"
            f"\n\n{meddelande}"
        ).strip()

        # Och materialet räknas som HÄMTAT under INV-BOOK-003.
        #
        # Utan den här raden fälls varje svar som citerar ett belopp från
        # kvittot kunden precis laddat upp: talet stod i FRÅGAN, inte i ett
        # verktygsresultat, och grinden känner bara till det senare. Det ÄR
        # hämtad data — den lästes ur filen i det här anropet — och att låtsas
        # annat hade gjort bilagan oanvändbar.
        forhamtat.append(
            _json.dumps(
                {"underlag": avläst, "text": bilaga.get("text", "")},
                ensure_ascii=False,
                default=str,
            )
        )

    svar = await run_bookkeeping_chat_turn(
        storage,
        tenant["tenant_id"],
        message=meddelande,
        historik=historik,
        forhamtat=forhamtat,
    )

    await storage.log_agent_run(
        tenant["tenant_id"],
        agent_type=AGENT_TYPE,
        pack_version=pack_version("bokforing/v1"),
        skills_used=[],
        input_text=meddelande[:4000],
        output_text=svar["reply"][:4000],
        step_log=[
            {
                "steg": "snajp:bokforing-chatt",
                "verktygsanrop": svar["verktygsanrop"],
                "grundad": svar["grundad"],
                "brister": svar["brister"],
            }
        ],
        tokens_in=0,
        tokens_out=0,
        latency_ms=svar["latency_ms"],
        model=f"{settings.llm_provider}:{settings.model}",
    )

    return {**svar, "underlag": bilaga}


@router.post("/api/bookkeeping/avstamning")
async def avstamning(
    request: Request,
    fran: date,
    till: date,
    fil: UploadFile = FastAPIFile(...),
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Stäm av ett kontoutdrag mot periodens underlag.

    ## Varför den INTE går genom `ta_emot_underlag`

    Ett kontoutdrag är inte ett underlag. Det bär inga momssatser och inga
    motparter att kontera — det bär betalningar som redan skett. Skickades det
    genom avläsningen hade varje rad blivit ett nonsensverifikat, och en fil med
    hundra rader hade producerat hundra av dem.

    Se `app/bookkeeping/kontoutdrag.py` för hela resonemanget.

    ## Den skriver ingenting

    Avstämningen är en LÄSNING: filen läses i minnet, jämförs mot underlagen och
    kastas. Ingen tabell, inget verifikat, ingen status som ändras. Därför är den
    ofarlig att köra om, och därför krävdes ingen migration för den.

    Den loggas inte heller till `agent_runs`: ingen modell körs, så det finns
    ingen körning att revidera. `agent_runs` är agentens logg, inte en
    åtkomstlogg.
    """
    data = await fil.read()
    try:
        transaktioner = las_kontoutdrag(data)
    except KontoutdragsfelError as felet:
        raise HTTPException(status_code=422, detail=str(felet)) from felet

    underlag = await request.app.state.storage.list_bk_underlag(
        tenant["tenant_id"], fran=fran, till=till
    )
    resultat = stam_av(transaktioner, underlag)

    return {
        "fran": fran.isoformat(),
        "till": till.isoformat(),
        "antal_transaktioner": len(transaktioner),
        "antal_underlag": len(underlag),
        "matchade": resultat.matchade,
        "saknar_underlag": resultat.saknar_underlag,
        "saknar_banktransaktion": resultat.saknar_banktransaktion,
        "sammanfattning": resultat.as_report(),
        "forbehall": FORBEHALL,
    }
