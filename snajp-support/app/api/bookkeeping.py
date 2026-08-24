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
    """
    kontrollera_fil(data, mimetyp)

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
        sha256=sha256_av(data),
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
    )

    return {
        "underlag": _underlag_ut(underlag),
        "status": avlasning.status,
        "brister": avlasning.verdikt.as_report(),
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

    return {**resultat, "forbehall": FORBEHALL}


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
    typ = request.headers.get("content-type") or ""

    meddelande = ""
    historik: list[dict[str, Any]] = []
    bilaga: dict[str, Any] | None = None

    if typ.startswith("multipart/form-data"):
        form = await request.form()
        meddelande = str(form.get("meddelande") or "").strip()
        rå_historik = form.get("historik")
        if isinstance(rå_historik, str) and rå_historik:
            import json as _json

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
        meddelande = f"{sammanfattning}\n\n{meddelande}".strip()

    svar = await run_bookkeeping_chat_turn(
        storage, tenant["tenant_id"], message=meddelande, historik=historik
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
