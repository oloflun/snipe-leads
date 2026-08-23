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

from ..agent.bookkeeping_agent import AGENT_TYPE, las_underlag
from ..agentcore.overlays import pack_version
from ..bookkeeping.math import (
    Konteringsrad,
    Post,
    moms_fran_brutto,
    netto_fran_brutto,
    summera_period,
)
from ..bookkeeping.sie4 import SieExportError, Verifikat, skriv_sie4
from ..bookkeeping.underlag import (
    UnderlagsfelError,
    kontrollera_fil,
    las_bild_text,
    las_pdf_text,
    sha256_av,
)
from ..bookkeeping.verifieringsgrind import STATUS_GRANSKA, STATUS_KLAR, check_period
from .deps import require_tenant

router = APIRouter()

#: Det juridiska förbehållet. Bor i backenden och inte bara i vyn: det följer
#: med i exporten också, och två kopior av samma text hade blivit två olika.
FORBEHALL = (
    "Förslag, inte bokföring. Snajp Bokföring föreslår kontering och räknar "
    "perioden. Förslagen är inte granskade av en auktoriserad "
    "redovisningskonsult och ersätter inte en. Du ansvarar för att uppgifterna "
    "är riktiga innan de förs in i ert bokföringssystem eller lämnas till "
    "Skatteverket."
)


def _kr(varde: Decimal | None) -> str | None:
    """Belopp som STRÄNG i JSON-svaret.

    Ett JSON-tal blir en float hos varje mottagare — webbläsaren räknar
    `0.1 + 0.2` till `0.30000000000000004` precis som Python gör. Hela
    modulens premiss är att belopp inte får bli float, och den premissen slutar
    inte gälla för att värdet passerat ett nätverk.
    """
    return None if varde is None else f"{varde:f}"


def _underlag_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {
        **{k: v for k, v in rad.items() if k not in ("brutto", "momssats", "tenant_id")},
        "brutto": _kr(rad.get("brutto")),
        "momssats": _kr(rad.get("momssats")),
    }


@router.post("/api/bookkeeping/underlag")
async def ladda_upp_underlag(
    request: Request,
    fil: UploadFile = FastAPIFile(...),
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Ta emot ett kvitto, läs av det, spara fälten — och kasta filen.

    Ordningen är hela poängen: filen finns bara i minnet under anropet, och
    det som skrivs till databasen är fälten plus en sha256. Se
    `app/bookkeeping/underlag.py`.
    """
    data = await fil.read()
    mimetyp = fil.content_type or ""
    try:
        kontrollera_fil(data, mimetyp)
    except UnderlagsfelError as fel:
        raise HTTPException(status_code=422, detail=str(fel)) from fel

    try:
        if mimetyp == "application/pdf":
            text = las_pdf_text(data)
            if not text:
                # En skannad PDF saknar textlager. Det är ett svar, inte ett
                # fel — och att säga vad kunden ska göra i stället är billigare
                # än att låta grinden fälla på "allt saknas".
                raise UnderlagsfelError(
                    "PDF:en saknar textlager (troligen en skanning). Ladda upp "
                    "den som bild i stället, så läses den av bildvägen."
                )
        else:
            import base64

            data_url = f"data:{mimetyp};base64,{base64.b64encode(data).decode()}"
            text = await las_bild_text(data_url)
    except UnderlagsfelError as fel:
        raise HTTPException(status_code=422, detail=str(fel)) from fel

    avlasning = await las_underlag(text)
    storage = request.app.state.storage

    underlag = await storage.create_bk_underlag(
        tenant["tenant_id"],
        sha256=sha256_av(data),
        filnamn=fil.filename or "underlag",
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
        befintliga = await storage.list_bk_verifikat(tenant["tenant_id"])
        await storage.create_bk_verifikat(
            tenant["tenant_id"],
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
        tenant["tenant_id"],
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
        "forbehall": FORBEHALL,
    }


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


async def _period(storage: Any, tenant_id: str, fran: date, till: date) -> dict[str, Any]:
    """Underlag, verifikat, grind och summor — i den ordningen.

    Summorna räknas ALDRIG före grinden. Att visa trovärdiga tal för en period
    som inte går ihop är värre än att visa inga alls — se STATUS.md 2026-08-16,
    där adminvyn gav fyra kunder med nollställda men rimliga siffror.
    """
    underlag = await storage.list_bk_underlag(tenant_id, fran=fran, till=till)
    verifikat = await storage.list_bk_verifikat(tenant_id, fran=fran, till=till)

    rader_per_verifikat = [
        [
            Konteringsrad(
                konto=r["konto"],
                debet=r["debet"],
                kredit=r["kredit"],
                text=r.get("text", ""),
            )
            for r in v["rader"]
        ]
        for v in verifikat
    ]
    verdikt = check_period(underlag=underlag, verifikat=rader_per_verifikat)

    # Summorna räknas bara på underlag som faktiskt har fälten. Ett fällt
    # underlag bidrar inte med ett gissat belopp — det står i brist-listan.
    #
    # Momsen räknas av `moms_fran_brutto`, inte här. En andra uträkning på den
    # här sidan hade varit en kopia som glider isär från den grinden och
    # verifikaten använder — och avrundningen hade dessutom saknats, så
    # periodsumman kunde avvika från verifikatens med några ören utan att
    # någonting sa ifrån.
    poster = []
    for u in underlag:
        if not (
            u.get("datum")
            and u.get("riktning")
            and u.get("brutto") is not None
            and u.get("momssats") is not None
        ):
            continue
        poster.append(
            Post(
                datum=date.fromisoformat(u["datum"]),
                riktning=u["riktning"],
                netto=netto_fran_brutto(u["brutto"], u["momssats"]),
                moms=moms_fran_brutto(u["brutto"], u["momssats"]),
                motpart=u.get("motpart") or "",
                underlag_id=u["id"],
            )
        )
    summor = summera_period(poster)

    return {
        "fran": fran.isoformat(),
        "till": till.isoformat(),
        "status": verdikt.status,
        "brister": verdikt.as_report(),
        "summor": {
            "intakter": _kr(summor.intakter),
            "kostnader": _kr(summor.kostnader),
            "utgaende_moms": _kr(summor.utgaende_moms),
            "ingaende_moms": _kr(summor.ingaende_moms),
            "resultat_fore_skatt": _kr(summor.resultat_fore_skatt),
            "moms_att_betala": _kr(summor.moms_att_betala),
            "antal_poster": summor.antal_poster,
        },
        "antal_underlag": len(underlag),
        "antal_verifikat": len(verifikat),
        "forbehall": FORBEHALL,
        "_verifikat": verifikat,
    }


@router.get("/api/bookkeeping/period")
async def periodrapport(
    request: Request,
    fran: date,
    till: date,
    tenant: dict = Depends(require_tenant),
) -> dict:
    rapport = await _period(request.app.state.storage, tenant["tenant_id"], fran, till)
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
    rapport = await _period(request.app.state.storage, tenant["tenant_id"], fran, till)
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
