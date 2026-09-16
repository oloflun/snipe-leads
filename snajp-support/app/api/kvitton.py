"""Kvittohanterarens endpoints.

## Vad agenten ALDRIG får göra härifrån

Den skickar ingenting, flyttar inga pengar och skriver aldrig i kundens
inkorg — mejlkopplingarna är read-only av konstruktion (se kvitton/mejl.py).
Allt den producerar är avlästa kvittofält en människa granskar.

## Förhållandet till /api/bookkeeping

Maskineriet (filkontroll, textutvinning, grind, lagring i bk_underlag,
SIE-export) delas med den gamla bokföringsytan. Det här är PRODUKTYTAN:
kvitton, kategorier, mejlskanning och sammanfattning. Gemensamma vägar
importeras — ingen andra läsväg skrivs (samma regel som ta_emot_underlag
dokumenterar).
"""

from __future__ import annotations

import base64
import csv
import io
import logging
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from fastapi import File as FastAPIFile

from ..agent.bookkeeping_agent import bygg_verifikat, las_underlag
from ..agent.kvitto_agent import (
    AGENT_TYPE,
    FORBEHALL,
    INTEGRITETSNOTIS,
    run_kvitto_chat_turn,
)
from ..agentcore.overlays import pack_version
from ..bookkeeping.kontoplan import KOSTNADSKATEGORIER
from ..bookkeeping.underlag import (
    UnderlagsfelError,
    kontrollera_fil,
    las_bild_text,
    las_pdf_text,
    normalisera_belopp,
    normalisera_falt,
    normalisera_momssats,
    sha256_av,
)
from ..bookkeeping.verifieringsgrind import STATUS_GRANSKA, check_underlag
from ..config import get_settings
from ..kvitton.mejl import MejlkontofelError, valj_mejlkonto
from ..kvitton.sammanfattning import (
    bara_utlagg,
    kategorietikett,
    sammanstall,
    summeringstext,
    svara_utan_modell,
    tolka_period_ur_fraga,
)
from ..kvitton.skanning import skanna_inkorg
from ..kvitton.tolkning import tolka_deterministiskt, valutaspärr
from .bookkeeping import _kvotsvar
from .deps import require_tenant

router = APIRouter()
logger = logging.getLogger("snajp-support.kvitton")


def _kvitto_ut(rad: dict[str, Any]) -> dict[str, Any]:
    """Radens JSON-form. Belopp som STRÄNGAR — se `kr` i bookkeeping/period.py."""
    return {
        "id": rad.get("id"),
        "datum": rad.get("datum"),
        "motpart": rad.get("motpart"),
        "filnamn": rad.get("filnamn"),
        "brutto": None if rad.get("brutto") is None else f"{rad['brutto']:f}",
        "momssats": None if rad.get("momssats") is None else f"{rad['momssats']:f}",
        "kategori": rad.get("kategori"),
        "kategorietikett": kategorietikett(rad.get("kategori")),
        "status": rad.get("status"),
        "betalstatus": rad.get("betalstatus"),
        "kalla": rad.get("kalla") or "uppladdning",
        "mejl_amne": rad.get("mejl_amne"),
        "mejl_avsandare": rad.get("mejl_avsandare"),
        # SEK så fort ett kronbelopp finns: ett godkänt utlandskvitto bär det
        # omräknade beloppet i brutto, och originalet står kvar i
        # belopp_original. Den lagrade valutan hade annars märkt kronorna USD.
        "valuta": "SEK" if rad.get("brutto") is not None else (rad.get("valuta") or "SEK"),
        "belopp_original": rad.get("belopp_original"),
        "anmarkning": rad.get("anmarkning") or "",
    }


async def _rader(request: Request, tenant_id: str, fran: date | None, till: date | None):
    # Utan tak: storage-lagrets standard är 200 rader, och en period med fler
    # kvitton gav summor som tyst stannade vid de 200 första.
    rader = await request.app.state.storage.list_bk_underlag(
        tenant_id, fran=fran, till=till, limit=100_000
    )
    return bara_utlagg(rader)


# -- Mejlkontot -------------------------------------------------------------


@router.get("/api/kvitton/mejlkonto")
async def mejlkonto(tenant: dict = Depends(require_tenant)) -> dict:
    """Vilken inkorg som är kopplad, eller att ingen är det.

    Kopplingen konfigureras per miljö (se kvitton/mejl.py om var tokens bor).
    Utan koppling visar gränssnittet vägen till att koppla — inte ett fel.
    """
    konto = valj_mejlkonto(tenant["tenant_id"])
    if konto is None:
        return {"kopplad": False, "integritetsnotis": INTEGRITETSNOTIS}
    return {
        "kopplad": True,
        "leverantor": konto.leverantor,
        "adress": konto.adress,
        "integritetsnotis": INTEGRITETSNOTIS,
    }


# -- Skanningen -------------------------------------------------------------


@router.post("/api/kvitton/skanna")
async def skanna(
    request: Request,
    fran: date | None = None,
    till: date | None = None,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Läs inkorgen, identifiera kvitton, extrahera och spara.

    Svaret bär en händelse per genomläst mejl (inkorgsvyns animation), de
    sparade kvittona och sammanfattningen — allt i ETT anrop, så att vyn
    aldrig kan visa en skanning och en tabell som inte hör ihop.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    konto = valj_mejlkonto(tenant["tenant_id"])
    if konto is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ingen mejlinkorg är kopplad ännu. Koppla Gmail eller Outlook under "
                "Inställningar, eller ladda upp kvitton manuellt."
            ),
        )

    try:
        resultat = await skanna_inkorg(storage, tenant_id, konto)
    except MejlkontofelError as fel:
        raise HTTPException(status_code=502, detail=str(fel)) from fel
    except Exception as fel:
        kvot = await _kvotsvar(storage, tenant_id, fel, dokument="inget")
        if kvot is None:
            raise
        return kvot

    settings = get_settings()
    await storage.log_agent_run(
        tenant_id,
        agent_type=AGENT_TYPE,
        pack_version=pack_version("bokforing/v1"),
        skills_used=[],
        input_text=f"kvittoskanning: {resultat.genomlasta} mejl ({konto.leverantor})",
        output_text=(
            f"{resultat.nya_kvitton} nya kvitton, "
            f"{resultat.hoppade_dubbletter} redan lästa"
        ),
        step_log=[{"steg": "snajp:kvitto-skanning", "handelser": len(resultat.handelser)}],
        tokens_in=0,
        tokens_out=0,
        latency_ms=0,
        model=f"{settings.llm_provider}:{settings.model}",
    )

    rader = await _rader(request, tenant_id, fran, till)
    samman = sammanstall(rader)
    return {
        "genomlasta": resultat.genomlasta,
        "nya_kvitton": resultat.nya_kvitton,
        "redan_lasta": resultat.hoppade_dubbletter,
        "handelser": resultat.handelser,
        "kvitton": [_kvitto_ut(r) for r in rader],
        "sammanfattning": {k: v for k, v in samman.items() if not k.startswith("_")},
        "text": summeringstext(
            samman,
            fran.isoformat() if fran else (rader[0].get("datum") or "") if rader else "",
            till.isoformat() if till else (rader[-1].get("datum") or "") if rader else "",
        ),
        "forbehall": FORBEHALL,
        "integritetsnotis": INTEGRITETSNOTIS,
    }


# -- Kvittolistan och sammanfattningen --------------------------------------


@router.get("/api/kvitton")
async def lista(
    request: Request,
    fran: date | None = None,
    till: date | None = None,
    tenant: dict = Depends(require_tenant),
) -> dict:
    rader = await _rader(request, tenant["tenant_id"], fran, till)
    return {
        "kvitton": [_kvitto_ut(r) for r in rader],
        "forbehall": FORBEHALL,
        "integritetsnotis": INTEGRITETSNOTIS,
    }


@router.get("/api/kvitton/sammanfattning")
async def sammanfattning(
    request: Request,
    fran: date,
    till: date,
    tenant: dict = Depends(require_tenant),
) -> dict:
    rader = await _rader(request, tenant["tenant_id"], fran, till)
    samman = sammanstall(rader)
    return {
        "fran": fran.isoformat(),
        "till": till.isoformat(),
        **{k: v for k, v in samman.items() if not k.startswith("_")},
        "text": summeringstext(samman, fran.isoformat(), till.isoformat()),
        "forbehall": FORBEHALL,
    }


@router.delete("/api/kvitton/period")
async def rensa_period(
    request: Request,
    fran: date,
    till: date,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Tömmer perioden. Äkta radering — samma semantik och samma lagringsväg
    som bokföringsytans rensning, se rensa_bk_period i storage/base.py."""
    antal = await request.app.state.storage.rensa_bk_period(
        tenant["tenant_id"], fran=fran, till=till
    )
    return {"raderade": antal}


# -- Manuell uppladdning -----------------------------------------------------


async def ta_emot_kvittofil(
    storage: Any, tenant_id: str, data: bytes, mimetyp: str, filnamn: str
) -> dict[str, Any]:
    """Kvittot in via fil: kontrollera, läs av, spara fälten — kasta filen.

    Samma ordning och samma dubblettspärr som bokföringens ta_emot_underlag.
    Skillnaderna: raden märks `kalla="uppladdning"`, och utan LLM-nyckel
    används den deterministiska läsaren i stället för att anropet faller —
    den lokala stacken och demon ska kunna ta emot en fil utan modell.
    """
    kontrollera_fil(data, mimetyp)

    sha256 = sha256_av(data)
    dubblett = await storage.get_bk_underlag_by_sha256(tenant_id, sha256)
    if dubblett is not None:
        beskrivning = dubblett.get("filnamn") or "ett kvitto"
        datum = dubblett.get("datum")
        raise UnderlagsfelError(
            f"Samma fil är redan uppladdad ({beskrivning}"
            + (f", {datum}" if datum else "")
            + "). Dubbletten sparades inte."
        )

    if mimetyp == "application/pdf":
        text = las_pdf_text(data)
        if not text:
            raise UnderlagsfelError(
                "PDF:en saknar textlager (troligen en skanning). Ladda upp "
                "den som bild i stället, så läses den av bildvägen."
            )
    else:
        data_url = f"data:{mimetyp};base64,{base64.b64encode(data).decode()}"
        text = await las_bild_text(data_url)

    settings = get_settings()
    valuta, belopp_original = "SEK", None
    if settings.is_simulation() or (
        (getattr(settings, "kvitto_tolkning", "") or "").strip().lower() == "deterministisk"
    ):
        avlast = tolka_deterministiskt(text)
        falt = normalisera_falt(avlast.falt)
        valuta, belopp_original = avlast.valuta, avlast.belopp_original
        verdikt = check_underlag(falt)
        verifikatrader = bygg_verifikat(falt) if verdikt.ok else ()
        status = verdikt.status
        brister = verdikt.as_report()
        # Bristerna in i anmärkningen: kvittolistan visar anmärkningen, och en
        # granska-rad utan förklaring är en fråga kunden inte kan besvara.
        anmarkning = "; ".join(
            dict.fromkeys(a for a in (avlast.anmarkning, *brister) if a)
        )
    else:
        avlasning = await las_underlag(text)
        falt, valuta, belopp_original, valutaanmarkning = valutaspärr(
            dict(avlasning.falt), text
        )
        anmarkning = avlasning.anmarkning or "; ".join(avlasning.verdikt.as_report())
        verifikatrader = avlasning.verifikat
        status = avlasning.status
        brister = avlasning.verdikt.as_report()
        if valuta != "SEK":
            # Modellens verifikat bygger på ett utländskt belopp läst som
            # kronor — det får varken sparas eller räknas. Kvittot väntar på
            # det omräknade beloppet i granskningskön.
            verifikatrader = ()
            status = STATUS_GRANSKA
            anmarkning = "; ".join(a for a in (valutaanmarkning, anmarkning) if a)

    underlag = await storage.create_bk_underlag(
        tenant_id,
        sha256=sha256,
        filnamn=filnamn or "kvitto",
        mimetyp=mimetyp,
        status=status,
        anmarkning=anmarkning,
        kalla="uppladdning",
        valuta=valuta,
        belopp_original=belopp_original,
        **{
            k: v
            for k, v in falt.items()
            if k in ("datum", "motpart", "brutto", "momssats", "riktning", "kategori", "betalstatus")
        },
    )

    if verifikatrader:
        befintliga = await storage.list_bk_verifikat(tenant_id)
        await storage.create_bk_verifikat(
            tenant_id,
            underlag_id=underlag["id"],
            serie="A",
            nummer=str(len(befintliga) + 1),
            datum=falt["datum"],
            text=falt.get("motpart", ""),
            rader=[
                {"konto": r.konto, "debet": r.debet, "kredit": r.kredit, "text": r.text}
                for r in verifikatrader
            ],
        )

    return {"underlag": _kvitto_ut(underlag), "status": status, "brister": brister}


@router.post("/api/kvitton/underlag")
async def ladda_upp(
    request: Request,
    fil: UploadFile = FastAPIFile(...),
    tenant: dict = Depends(require_tenant),
) -> dict:
    try:
        resultat = await ta_emot_kvittofil(
            request.app.state.storage,
            tenant["tenant_id"],
            await fil.read(),
            fil.content_type or "",
            fil.filename or "kvitto",
        )
    except UnderlagsfelError as fel:
        raise HTTPException(status_code=422, detail=str(fel)) from fel
    except Exception as fel:
        kvot = await _kvotsvar(
            request.app.state.storage, tenant["tenant_id"], fel, dokument="ej_sparat"
        )
        if kvot is None:
            raise
        return kvot
    return {**resultat, "forbehall": FORBEHALL}


# -- Godkännande av flaggade kvitton ----------------------------------------


@router.post("/api/kvitton/{kvitto_id}/godkann")
async def godkann(
    request: Request,
    kvitto_id: str,
    kropp: dict | None = None,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Människans ja till ett flaggat kvitto, med möjlighet att rätta fält.

    Kroppen får bära brutto/momssats/kategori/datum/motpart/betalstatus.
    Grinden körs IGEN på det rättade kvittot: ett godkännande är inte en väg
    förbi kontrollen utan ett sätt att komplettera den — saknas fortfarande
    ett fält förblir kvittot i granskningskön, med beskedet varför.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    # Ett id som inte är en uuid är ett kvitto som inte finns. Postgres hade
    # annars kastat på typkonverteringen och svarat 500.
    try:
        uuid.UUID(kvitto_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Kvittot finns inte.") from None
    rad = await storage.get_bk_underlag(tenant_id, kvitto_id)
    if rad is None:
        raise HTTPException(status_code=404, detail="Kvittot finns inte.")
    if rad.get("status") != STATUS_GRANSKA:
        # Ett klart kvitto har redan ett verifikat. Att rätta beloppet här hade
        # lämnat verifikatet på det gamla — summan och SIE-exporten hade sagt
        # två olika saker. Rättelse av klara kvitton är ett eget flöde.
        raise HTTPException(
            status_code=409,
            detail="Kvittot är redan godkänt. Rensa perioden och läs in det igen för att rätta det.",
        )

    kropp = kropp or {}
    andringar: dict[str, Any] = {}
    motpart = kropp.get("motpart")
    if isinstance(motpart, str) and motpart.strip():
        andringar["motpart"] = motpart.strip()
    kategori = kropp.get("kategori")
    if isinstance(kategori, str) and kategori.strip():
        # Validerad HÄR: en okänd kategori hade passerat grinden (den kräver
        # bara att fältet finns) och sedan kastat OkantKontoError i
        # verifikatbygget — ett 500 i stället för ett besked.
        if kategori.strip() not in KOSTNADSKATEGORIER:
            raise HTTPException(
                status_code=422,
                detail=f"Okänd kategori. Välj en av: {', '.join(sorted(KOSTNADSKATEGORIER))}.",
            )
        andringar["kategori"] = kategori.strip()
    betalstatus = kropp.get("betalstatus")
    if isinstance(betalstatus, str) and betalstatus.strip():
        if betalstatus.strip() not in ("betald", "obetald"):
            raise HTTPException(status_code=422, detail="Betalstatus ska vara betald eller obetald.")
        andringar["betalstatus"] = betalstatus.strip()
    if isinstance(kropp.get("datum"), str) and kropp["datum"].strip():
        try:
            andringar["datum"] = date.fromisoformat(kropp["datum"].strip())
        except ValueError:
            raise HTTPException(status_code=422, detail="Datum ska vara ÅÅÅÅ-MM-DD.")
    brutto = kropp.get("brutto")
    if isinstance(brutto, bool):
        brutto = None
    if isinstance(brutto, (str, int, float)) and str(brutto).strip():
        tolkat = normalisera_belopp(str(brutto).replace(" ", "").replace(",", "."))
        if tolkat is None or tolkat <= 0:
            raise HTTPException(status_code=422, detail="Beloppet går inte att tolka.")
        andringar["brutto"] = tolkat
    sats = kropp.get("momssats")
    if isinstance(sats, bool):
        sats = None
    if isinstance(sats, (str, int, float)) and str(sats).strip():
        tolkad = normalisera_momssats(str(sats))
        if tolkad is None:
            raise HTTPException(status_code=422, detail="Momssatsen ska vara 25, 12, 6 eller 0 %.")
        andringar["momssats"] = tolkad

    # Riktningen sätts: produkten tar bara emot utlägg, så en rad utan riktning
    # är en kostnad. BETALSTATUS sätts däremot ALDRIG av koden — den avgör
    # motkontot (1930 mot 2440, se kontoplan.BETALKONTO_INKOP), och en tyst
    # "betald" bokför en obetald faktura mot bankkontot. Saknas den frågar
    # gränssnittet, och grinden nedan fäller tills svaret finns.
    if not rad.get("riktning"):
        andringar["riktning"] = "kostnad"

    if andringar:
        rad = await storage.update_bk_underlag(tenant_id, kvitto_id, **andringar)

    kontroll = {
        k: rad.get(k)
        for k in ("datum", "motpart", "brutto", "momssats", "riktning", "kategori", "betalstatus")
    }
    verdikt = check_underlag(kontroll)
    if not verdikt.ok:
        return {
            "godkand": False,
            "brister": verdikt.as_report(),
            "underlag": _kvitto_ut(rad),
        }

    rad = await storage.update_bk_underlag(
        tenant_id, kvitto_id, status="klar", anmarkning="Godkänt manuellt."
    )
    # Verifikat byggs vid godkännandet om kvittot saknar ett — grinden har
    # precis sagt ja, och ett klart kvitto utan verifikat fäller perioden.
    befintliga = await storage.list_bk_verifikat(tenant_id)
    if not any(v.get("underlag_id") == kvitto_id for v in befintliga):
        from datetime import date as _date

        falt = {
            **kontroll,
            "datum": _date.fromisoformat(str(rad["datum"])),
        }
        rader = bygg_verifikat(falt)
        await storage.create_bk_verifikat(
            tenant_id,
            underlag_id=kvitto_id,
            serie="A",
            nummer=str(len(befintliga) + 1),
            datum=falt["datum"],
            text=str(falt.get("motpart") or ""),
            rader=[
                {"konto": r.konto, "debet": r.debet, "kredit": r.kredit, "text": r.text}
                for r in rader
            ],
        )
    return {"godkand": True, "underlag": _kvitto_ut(rad)}


# -- Exporten ---------------------------------------------------------------


@router.get("/api/kvitton/export.csv")
async def exportera_csv(
    request: Request,
    fran: date,
    till: date,
    tenant: dict = Depends(require_tenant),
) -> Response:
    """Kvittona som CSV — för Excel eller vidare in i ett bokföringssystem.

    SIE-exporten (Fortnox, Visma, Bokio m.fl.) finns kvar oförändrad på
    `GET /api/bookkeeping/period.sie` och bygger på samma verifikat.
    """
    rader = await _rader(request, tenant["tenant_id"], fran, till)
    buffert = io.StringIO()
    writer = csv.writer(buffert, delimiter=";")
    # Två beloppskolumner, inte belopp + valuta: ett godkänt utlandskvitto
    # bär både det omräknade SEK-beloppet och originalet, och en ensam
    # valutakolumn hade märkt kronbeloppet som USD.
    writer.writerow(
        [
            "Datum",
            "Leverantör",
            "Belopp (SEK)",
            "Originalbelopp",
            "Moms",
            "Kategori",
            "Källa",
            "Status",
            "Anmärkning",
        ]
    )
    for r in rader:
        writer.writerow(
            [
                r.get("datum") or "",
                r.get("motpart") or r.get("filnamn") or "",
                "" if r.get("brutto") is None else f"{r['brutto']:f}",
                r.get("belopp_original") or "",
                "" if r.get("momssats") is None else f"{r['momssats']:f}",
                kategorietikett(r.get("kategori")),
                r.get("kalla") or "uppladdning",
                r.get("status") or "",
                r.get("anmarkning") or "",
            ]
        )
    # BOM så att Excel på svenska Windows läser å/ä/ö rätt utan importdialog.
    data = "\ufeff" + buffert.getvalue()
    return Response(
        content=data.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="kvitton-{fran.isoformat()}-{till.isoformat()}.csv"'
            )
        },
    )


# -- Assistenten ------------------------------------------------------------


@router.post("/api/kvitton/chat")
async def chatt(
    request: Request,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Kvitto-assistenten. Ett meddelande in, ett grundat svar ut.

    Utan LLM-nyckel (simuleringsläge) svarar svarsmotorn i
    kvitton/sammanfattning.py — kod, inte modell, samma summor som tabellen.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    kropp = await request.json()
    meddelande = str(kropp.get("meddelande") or "").strip()
    historik = kropp.get("historik") or []
    if not meddelande:
        raise HTTPException(status_code=422, detail="Skriv en fråga.")

    settings = get_settings()
    if settings.is_simulation():
        idag = date.today()
        from calendar import monthrange

        standard_fran = idag.replace(day=1).isoformat()
        standard_till = idag.replace(day=monthrange(idag.year, idag.month)[1]).isoformat()
        fran, till = tolka_period_ur_fraga(
            meddelande, standard_fran=standard_fran, standard_till=standard_till, ar=idag.year
        )
        rader = await storage.list_bk_underlag(
            tenant_id, fran=date.fromisoformat(fran), till=date.fromisoformat(till)
        )
        return {
            "reply": svara_utan_modell(meddelande, rader, fran, till),
            "grundad": True,
            "brister": [],
            "verktygsanrop": 1,
            "latency_ms": 0,
            "forbehall": FORBEHALL,
            "simulerad": True,
        }

    try:
        svar = await run_kvitto_chat_turn(
            storage, tenant_id, message=meddelande, historik=historik
        )
    except Exception as fel:
        kvot = await _kvotsvar(storage, tenant_id, fel, dokument="inget")
        if kvot is None:
            raise
        return kvot

    await storage.log_agent_run(
        tenant_id,
        agent_type=AGENT_TYPE,
        pack_version=pack_version("bokforing/v1"),
        skills_used=[],
        input_text=meddelande[:4000],
        output_text=svar["reply"][:4000],
        step_log=[
            {
                "steg": "snajp:kvitto-chatt",
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
    return svar
