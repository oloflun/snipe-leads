"""Flytta till main — den ENDA vägen från development till produktion (plan del E).

Antons beställning 2026-10-01: development speglas från main varje natt
(envägs, inget skrivs tillbaka), men en admin ska via Byt kund kunna välja,
markera och flytta supportmejl eller leadskörningar till main när något ska
sparas till den riktiga miljön. Det får vara den enda vägen.

## Hur vägen är låst (INV-DATA-003)

- **Paketet signeras** med HMAC-SHA256 över exakt den JSON som skickas, med
  `FLYTT_NYCKEL` som bara finns som miljövariabel i main och development.
  Mottagaren verifierar signaturen innan den läser en byte av innehållet.
- **Mottagaren vägrar i en spegel.** `/importera` kontrollerar att databasen
  saknar `mirror_meta` (markören spegelskriptet sätter). Development kan
  alltså aldrig importera till sig själv eller till en annan spegel, och
  main (som aldrig speglats) är det enda giltiga målet.
- **Mottagaren kräver ingen masternyckel** — den kan inte, eftersom
  avsändaren är en annan miljös api med en annan nyckel. HMAC:en är
  behörigheten, och den utan nyckel kan inte producera en.
- **Idempotent.** Mejl dedupliceras på provider_message_id (save_email
  returnerar None vid dublett), prospekt på bolagsnamn, körningar på job_id.
  Att flytta samma sak två gånger ger kvittot "redan flyttad".
- **Spårbart.** Varje importerad rad bär `importerad_fran='development'` i
  beslutsloggen (mejl) respektive profilen (prospekt), och development
  loggar varje flytt i `dev_flytt_ko` (migration 085).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import get_settings
from ..storage.base import BEDOMNINGSFALT
from .deps import require_master_key

logger = logging.getLogger("snajp-support.admin-flytt")

router = APIRouter(prefix="/api/admin/flytt", dependencies=[Depends(require_master_key)])
#: Mottagaren: HMAC i stället för masternyckel, se modulens docstring.
mottag = APIRouter(prefix="/api/admin/flytt")

SIGNATURHUVUD = "X-Flytt-Signatur"
#: Nästa nattliga spegling (.github/workflows/spegla-dev.yml, cron 0 2 * * * UTC).
NASTA_SPEGLING = "04:00 svensk sommartid (02:00 UTC)"


class FlyttRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=120)
    typ: Literal["mejl", "korning"]
    ids: list[str] = Field(..., min_length=1, max_length=50)


# -- Signering ---------------------------------------------------------------


def _kanonisk(paket: dict[str, Any]) -> bytes:
    return json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def signera(paket: dict[str, Any], nyckel: str) -> str:
    return hmac.new(nyckel.encode("utf-8"), _kanonisk(paket), hashlib.sha256).hexdigest()


def _kraev_nyckel() -> str:
    nyckel = get_settings().flytt_nyckel
    if not nyckel:
        raise HTTPException(status_code=503, detail="FLYTT_NYCKEL är inte satt i den här miljön.")
    return nyckel


# -- Uppslag -----------------------------------------------------------------


async def _tenant_for_slug(storage, slug: str) -> dict[str, Any]:
    for t in await storage.list_tenants():
        if str(t.get("slug") or "") == slug:
            return t
    raise HTTPException(status_code=404, detail="Kunden finns inte.")


_MEJLFALT = (
    "provider", "provider_message_id", "from_email", "from_name", "subject", "body_text",
    "received_at", "is_test", "status", "klass", "klass_kalla",
)
_KLASSFALT = (
    "category", "priority", "sentiment", "confidence", "escalate", "escalation_reason",
    "reasoning", "kb_sources", "model",
)
_PROSPEKTFALT = (
    "company_name", "contact_name", "contact_email", "origin", "website", "ort", "postnr",
    "orgnr", "sni", "anstallda", "omsattning", "contact_role", "contact_level",
    "contact_form_url", "contact_phone", "niva", "score_total", "score_breakdown",
    "motivering", "icp_fit", "qualified", "disqualifiers", "lagesbeskrivning", "signaler",
    "status", "webbrevision", "profil_version", "jev",
)


async def _bygg_paket(storage, tenant: dict[str, Any], typ: str, ids: list[str]) -> dict[str, Any]:
    tenant_id = str(tenant["id"])
    poster: list[dict[str, Any]] = []
    if typ == "mejl":
        for mid in ids:
            rad = await storage.get_email(tenant_id, mid)
            if not rad:
                raise HTTPException(status_code=404, detail=f"Mejlet {mid} finns inte.")
            k = rad.get("classification") or {}
            poster.append({
                "ref_id": str(rad["id"]),
                **{f: rad.get(f) for f in _MEJLFALT},
                "classification": {f: k.get(f) for f in _KLASSFALT} if k else None,
            })
    else:
        for bid in ids:
            korning = await storage.get_leads_korning(tenant_id, bid)
            if not korning:
                raise HTTPException(status_code=404, detail=f"Körningen {bid} finns inte.")
            prospekt = []
            for j in (korning.get("korning") or {}).get("jobs") or []:
                pid = j.get("prospect_id")
                p = await storage.get_prospect(tenant_id, pid) if pid else None
                if p:
                    prospekt.append({f: p.get(f) for f in _PROSPEKTFALT})
            poster.append({
                "ref_id": str(korning["job_id"]),
                "korning": {f: korning.get(f) for f in ("job_id", "status", "scope", "is_test", "error", "korning")},
                "prospekt": prospekt,
            })
    return {
        "version": 1,
        "fran": get_settings().aktiv_miljo() or "development",
        "tenant_id": tenant_id,
        "tenant_slug": str(tenant.get("slug") or ""),
        "typ": typ,
        "poster": poster,
    }


# -- Avsändarsidan (development, masternyckel) ---------------------------------


@router.get("/status")
async def flytt_status(request: Request) -> dict:
    """Är den här miljön en spegel, när speglas den nästa gång, och är
    flyttvägen konfigurerad. Panelen i Byt kund renderas bara i en spegel."""
    s = get_settings()
    return {
        "spegel": await request.app.state.storage.spegel_info(),
        "nasta_spegling": NASTA_SPEGLING,
        "mal_konfigurerat": bool(s.flytt_mal_url),
        "nyckel_konfigurerad": bool(s.flytt_nyckel),
    }


@router.get("/kandidater")
async def flytt_kandidater(request: Request, slug: str) -> dict:
    """Det som går att flytta för EN kund: de senaste mejlen och körningarna,
    plus kvittona på vad som redan flyttats."""
    storage = request.app.state.storage
    tenant = await _tenant_for_slug(storage, slug)
    tenant_id = str(tenant["id"])
    mejl = await storage.list_emails(tenant_id, limit=30, is_test=None, inkludera_larm=True)
    korningar = await storage.list_leads_korningar(tenant_id, limit=10)
    return {
        "tenant_id": tenant_id,
        "mejl": [
            {k: m.get(k) for k in ("id", "subject", "from_email", "status", "klass", "received_at", "is_test")}
            for m in mejl
        ],
        "korningar": [
            {
                "job_id": k["job_id"], "status": k["status"], "scope": k["scope"],
                "created_at": k.get("created_at"), "is_test": k.get("is_test"),
                "mal": (k.get("korning") or {}).get("mal"),
                "levererade": (k.get("korning") or {}).get("levererade"),
            }
            for k in korningar
        ],
        "flyttade": await storage.list_flytt(tenant_id, limit=50),
    }


@router.post("/paket")
async def flytt_paket(request: Request, payload: FlyttRequest) -> dict:
    """Paketet och dess signatur, utan att skicka — för granskning och test."""
    storage = request.app.state.storage
    tenant = await _tenant_for_slug(storage, payload.slug)
    paket = await _bygg_paket(storage, tenant, payload.typ, payload.ids)
    return {"paket": paket, "signatur": signera(paket, _kraev_nyckel())}


@router.post("/skicka")
async def flytt_skicka(request: Request, payload: FlyttRequest) -> dict:
    """Bygger paketet, signerar och skickar det till main. Kvitto per rad
    loggas i dev_flytt_ko så spegelskriptet ser en misslyckad flytt."""
    s = get_settings()
    if not s.flytt_mal_url:
        raise HTTPException(status_code=503, detail="FLYTT_MAL_URL är inte satt: ingen mottagare att skicka till.")
    storage = request.app.state.storage
    tenant = await _tenant_for_slug(storage, payload.slug)
    tenant_id = str(tenant["id"])
    paket = await _bygg_paket(storage, tenant, payload.typ, payload.ids)
    kropp = _kanonisk(paket)
    signatur = hmac.new(_kraev_nyckel().encode("utf-8"), kropp, hashlib.sha256).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            svar = await client.post(
                s.flytt_mal_url.rstrip("/") + "/api/admin/flytt/importera",
                content=kropp,
                headers={"Content-Type": "application/json", SIGNATURHUVUD: signatur},
            )
        utfall = svar.json() if svar.headers.get("content-type", "").startswith("application/json") else {}
        if svar.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Main svarade {svar.status_code}: {utfall.get('detail') or svar.text[:200]}")
    except HTTPException:
        for pid in payload.ids:
            await storage.logga_flytt(tenant_id, typ=payload.typ, ref_id=pid, resultat="fel")
        raise
    except Exception as fel:  # noqa: BLE001 — nätfel ska bli ett kvitto, inte en 500
        for pid in payload.ids:
            await storage.logga_flytt(tenant_id, typ=payload.typ, ref_id=pid, resultat="fel")
        raise HTTPException(status_code=502, detail=f"Kunde inte nå main: {fel}") from fel
    for rad in utfall.get("rader") or []:
        await storage.logga_flytt(
            tenant_id, typ=payload.typ, ref_id=str(rad.get("ref_id")),
            resultat="ok" if rad.get("resultat") in ("importerad", "redan_flyttad") else "fel",
        )
    return utfall


# -- Mottagarsidan (main, HMAC) ------------------------------------------------


@mottag.post("/importera")
async def flytt_importera(
    request: Request, x_flytt_signatur: str | None = Header(default=None, alias=SIGNATURHUVUD)
) -> dict:
    """Tar emot ett signerat paket. Vägrar utan giltig signatur (403) och i
    en spegel (409). Idempotent per rad."""
    nyckel = _kraev_nyckel()
    kropp = await request.body()
    vantad = hmac.new(nyckel.encode("utf-8"), kropp, hashlib.sha256).hexdigest()
    if not x_flytt_signatur or not hmac.compare_digest(vantad, x_flytt_signatur):
        raise HTTPException(status_code=403, detail="Ogiltig signatur.")
    storage = request.app.state.storage
    if await storage.spegel_info():
        raise HTTPException(status_code=409, detail="Den här miljön är en spegel och tar inte emot flyttar.")
    try:
        paket = json.loads(kropp)
    except ValueError as fel:
        raise HTTPException(status_code=422, detail="Paketet är inte giltig JSON.") from fel
    if paket.get("version") != 1 or paket.get("typ") not in ("mejl", "korning"):
        raise HTTPException(status_code=422, detail="Okänt paketformat.")
    tenant_id = str(paket.get("tenant_id") or "")
    if not tenant_id or not await storage.get_tenant(tenant_id):
        raise HTTPException(status_code=404, detail="Kunden finns inte i den här miljön.")
    fran = str(paket.get("fran") or "development")
    rader: list[dict[str, Any]] = []
    for post in paket.get("poster") or []:
        try:
            if paket["typ"] == "mejl":
                rader.append(await _importera_mejl(storage, tenant_id, post, fran))
            else:
                rader.append(await _importera_korning(storage, tenant_id, post, fran))
        except Exception as fel:  # noqa: BLE001 — en rad som faller stoppar inte resten
            logger.exception("Import av %s föll", post.get("ref_id"))
            rader.append({"ref_id": post.get("ref_id"), "resultat": "fel", "fel": str(fel)[:200]})
    return {"rader": rader, "importerade": sum(1 for r in rader if r["resultat"] == "importerad")}


async def _importera_mejl(storage, tenant_id: str, post: dict[str, Any], fran: str) -> dict[str, Any]:
    rad = await storage.save_email(
        tenant_id,
        provider=str(post.get("provider") or "mock"),
        provider_message_id=str(post.get("provider_message_id") or post["ref_id"]),
        from_email=str(post.get("from_email") or ""),
        from_name=post.get("from_name"),
        subject=str(post.get("subject") or ""),
        body_text=str(post.get("body_text") or ""),
        received_at=post.get("received_at"),
        is_test=bool(post.get("is_test")),
    )
    if rad is None:
        return {"ref_id": post["ref_id"], "resultat": "redan_flyttad"}
    await storage.update_email(
        tenant_id, rad["id"], status=post.get("status") or None,
        klass=post.get("klass") or None, klass_kalla=post.get("klass_kalla") or None,
    )
    k = post.get("classification")
    if k and k.get("category"):
        await storage.save_classification(
            tenant_id, email_id=rad["id"], category=k["category"], priority=k.get("priority") or "normal",
            sentiment=k.get("sentiment"), confidence=float(k.get("confidence") or 0.5),
            escalate=bool(k.get("escalate")), escalation_reason=k.get("escalation_reason"),
            reasoning=str(k.get("reasoning") or ""), kb_sources=list(k.get("kb_sources") or []),
            model=str(k.get("model") or "import"),
        )
    await storage.log_decision(
        tenant_id, email_id=rad["id"], event="importerad",
        detail={"importerad_fran": fran, "ref_id": post["ref_id"]},
    )
    return {"ref_id": post["ref_id"], "resultat": "importerad", "id": rad["id"]}


async def _importera_korning(storage, tenant_id: str, post: dict[str, Any], fran: str) -> dict[str, Any]:
    k = post.get("korning") or {}
    job_id = str(k.get("job_id") or post["ref_id"])
    if await storage.get_leads_korning(tenant_id, job_id):
        return {"ref_id": post["ref_id"], "resultat": "redan_flyttad"}
    befintliga = {str(p.get("company_name") or "").casefold(): p for p in await storage.list_prospects(tenant_id, limit=500)}
    nya = 0
    for p in post.get("prospekt") or []:
        namn = str(p.get("company_name") or "").strip()
        if not namn or namn.casefold() in befintliga:
            continue
        profil = {f: p[f] for f in _PROSPEKTFALT if f not in ("company_name", "contact_name", "contact_email", "origin") and p.get(f) is not None}
        profil["importerad_fran"] = fran
        skapad = await storage.create_prospect(
            tenant_id, company_name=namn, contact_name=p.get("contact_name"),
            contact_email=p.get("contact_email"),
            origin=str(p.get("origin") or "import") if p.get("origin") in ("manual", "example", "import", "test", "inkorg", "lista", "iris") else "import",
            profil=profil,
        )
        # Bedömningen följer med (2026-10-05): create_prospect tar bara
        # grundfälten, så nivå, poäng, motivering, kriterier, lägesbeskrivning
        # och webbrevisionen föll bort och leadet landade i main obedömt.
        bedomning = {f: p[f] for f in BEDOMNINGSFALT if p.get(f) is not None}
        if bedomning:
            await storage.spara_bedomning(tenant_id, skapad["id"], bedomning=bedomning)
        nya += 1
    await storage.set_leads_job_status(
        tenant_id, job_id=job_id, status=str(k.get("status") or "completed"), scope=str(k.get("scope") or "batch"),
        korning={**(k.get("korning") or {}), "importerad_fran": fran}, error=k.get("error"), is_test=bool(k.get("is_test")),
    )
    return {"ref_id": post["ref_id"], "resultat": "importerad", "prospekt": nya}
