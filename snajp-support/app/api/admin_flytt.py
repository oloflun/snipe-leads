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
  returnerar None vid dublett), prospekt på bolagsnamn, körningar på job_id
  och utkast på att tråden redan bär ett väntande utkast. Att flytta samma
  sak två gånger ger kvittot "redan flyttad" — men en omflytt KOMPLETTERAR
  det som saknas (prospekt eller utkast som en äldre flytt inte bar), med
  kvittot "kompletterad", i stället för att stanna vid job_id-dubbletten.
- **Utkasten följer med** (Sebbe 2026-10-20, handoffen 2026-10-17 punkt 4):
  varje prospekt i en körnings- eller prospektflytt bär sitt väntande utkast
  (osänt, ej kasserat) med köpostens status, tid och gate_checks. Ett
  godkännande gjort i development skrivs om till `godkand_i='main'` — main
  är den miljö som skickar (scheduler.skickas_har), samma omskrivning som
  första synken gjorde. Trådens language_state följer inte med: 'sv' är
  utgångsläget och en_confirmed kräver ett inkommet engelskt svar, vilket
  inte kan finnas i development sedan utskicken flyttade till main.
- **Spårbart.** Varje importerat mejl bär `importerad_fran='development'` i
  beslutsloggen, listor i plattformshändelsen, och development loggar varje
  flytt i `dev_flytt_ko` (migration 085, alla typer sedan 112). Prospekt har
  ingen kolumn för det (085: "ingen ny kolumn"); fältet filtreras bort.

## Listor, och att det flyttade blir skarpt (Sebbe 2026-10-18)

Leadslistor flyttas med alla rader (`typ='lista'`). Allt en admin gör när den
"testar som" en kund märks som test (prospekt med origin 'test', listor med
is_test), och synken för aldrig över test (scripts/railway_synk.py). Flytten
är adminens uttryckliga val att spara något till den riktiga miljön, så det
som flyttas blir skarpt i main: origin 'test'/'example' blir 'import' och en
lista importeras med is_test = false. Annars hade det landat i main osynligt
på kundens riktiga profil, vilket var precis felet som fick Alunix listor att
saknas. Dedup för listor är titeln hos kunden; raderna filtreras mot bolag
kunden redan har (app/leads/upptagna.py), som när en lista kopieras.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from ..config import get_settings
from ..leads import upptagna
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
    typ: Literal["mejl", "korning", "prospekt", "lista"]
    ids: list[str] = Field(..., min_length=1)


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


#: Listradens fält i en flytt. Samma kund i båda miljöerna, så
#: webbplatsbedömningen (lan, webbniva, webbrevision) följer med; den lämnar
#: aldrig kunden (jämför admin_listor.LISTRADSFALT, som saknar dem med flit).
_LISTRADSFALT = (
    "item_typ", "company_name", "website", "ort", "contact_name", "contact_role",
    "contact_email", "contact_level", "contact_phone", "orgnr", "source_name",
    "source_url", "signal", "signal_detalj", "lan", "postnr", "webbniva", "webbrevision",
)
_LISTFALT = ("titel", "icp", "antal", "kalla", "kontaktfilter", "status", "is_test")


def _skarp_origin(origin: Any) -> str:
    """Origin i main efter en flytt: testmärkningen tas bort, se docstringen."""
    if origin in ("manual", "import", "inkorg", "lista", "iris"):
        return str(origin)
    return "import"


#: Dedupen läser kundens ALLA prospekt. 500 (list_prospects default) var för
#: lågt redan 2026-10-20 (snajp hade 873 i main): varje bolag utanför de 500
#: senaste hade blivit en dublett vid nästa flytt.
_DEDUP_TAK = 5000


async def _utkast_for(storage, tenant_id: str, prospect_id: str) -> dict[str, Any] | None:
    """Prospektets väntande utkast (osänt, ej kasserat) med trådens senaste
    köpost — det som annars blev kvar i development när körningen flyttades
    (handoffen 2026-10-17, punkt 4: "utkasten måste skapas om i main")."""
    trad = await storage.find_outreach_thread(tenant_id, prospect_id=prospect_id)
    if not trad:
        return None
    m = await storage.get_pending_outreach_message(tenant_id, str(trad["id"]))
    if not m or not str(m.get("body") or "").strip():
        return None
    lagen = (await storage.utkast_lagen(tenant_id, prospect_id=prospect_id)).get(str(prospect_id)) or {}
    gate = lagen.get("gate_checks")
    if isinstance(gate, str):
        gate = json.loads(gate or "{}")
    return {
        "subject": m.get("subject"),
        "body": m.get("body"),
        "humanizer_variant": m.get("humanizer_variant"),
        "ko_status": lagen.get("ko_status"),
        "scheduled_at": lagen.get("scheduled_at"),
        "gate_checks": gate,
    }


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
    elif typ == "prospekt":
        # Enstaka leads, markerade i leadsvyn (Sebbe 2026-10-06): paketet bär
        # samma fält som körningsflytten, utan körningen runt omkring.
        for pid in ids:
            p = await storage.get_prospect(tenant_id, pid)
            if not p:
                raise HTTPException(status_code=404, detail=f"Leadet {pid} finns inte.")
            poster.append({
                "ref_id": pid,
                "prospekt": [{f: p.get(f) for f in _PROSPEKTFALT}],
                "utkast": await _utkast_for(storage, tenant_id, pid),
            })
    elif typ == "lista":
        for lid in ids:
            lista = await storage.get_lead_list(tenant_id, lid)
            if not lista:
                raise HTTPException(status_code=404, detail=f"Listan {lid} finns inte.")
            rader = await storage.list_lead_list_items(tenant_id, lid)
            poster.append({
                "ref_id": lid,
                "lista": {f: lista.get(f) for f in _LISTFALT},
                "rader": [{f: r.get(f) for f in _LISTRADSFALT} for r in rader],
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
                    prospekt.append({
                        **{f: p.get(f) for f in _PROSPEKTFALT},
                        "utkast": await _utkast_for(storage, tenant_id, str(pid)),
                    })
            poster.append({
                "ref_id": str(korning["job_id"]),
                "korning": {f: korning.get(f) for f in ("job_id", "status", "scope", "is_test", "error", "korning")},
                "prospekt": prospekt,
            })
    # jsonable_encoder: Decimal (omsättning, poäng), datetime och UUID ur
    # databasraderna blir JSON-värden. Utan den föll signeringen (_kanonisk)
    # med "Object of type Decimal is not JSON serializable" och flytten
    # svarade 500 (Alunix bolag 2026-10-18). Samma form som /paket returnerar.
    return jsonable_encoder({
        "version": 1,
        "fran": get_settings().aktiv_miljo() or "development",
        "tenant_id": tenant_id,
        "tenant_slug": str(tenant.get("slug") or ""),
        "typ": typ,
        "poster": poster,
    })


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
    # 200 och inte 10 (Sebbe 2026-10-20): alla körningar gjorda i development
    # ska gå att flytta genom knappen, inte bara de tio senaste.
    korningar = await storage.list_leads_korningar(tenant_id, limit=200)
    listor = await storage.list_lead_lists(tenant_id, limit=30)
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
        "listor": [
            {
                "id": str(lista["id"]), "titel": lista.get("titel"), "status": lista.get("status"),
                "kalla": lista.get("kalla"), "is_test": lista.get("is_test"),
                "rader": lista.get("item_count"), "created_at": lista.get("created_at"),
            }
            for lista in listor
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
            resultat="ok" if rad.get("resultat") in ("importerad", "redan_flyttad", "kompletterad") else "fel",
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
    if paket.get("version") != 1 or paket.get("typ") not in ("mejl", "korning", "prospekt", "lista"):
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
            elif paket["typ"] == "prospekt":
                rader.append(await _importera_prospekt(storage, tenant_id, post, fran))
            elif paket["typ"] == "lista":
                rader.append(await _importera_lista(storage, tenant_id, post, fran))
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


#: Köstatusar en utkastflytt bevarar. Allt annat (sent, cancelled — ska inte
#: kunna förekomma: ett kasserat utkast exporteras aldrig) blir granskning.
_UTKASTSTATUSAR = ("queued", "awaiting_review", "blocked")


async def _importera_utkast(storage, tenant_id: str, prospect_id: str, utkast: Any, fran: str) -> bool:
    """Prospektets väntande utkast med sin köpost, in i mottagarens tråd.

    Dedup: en tråd som redan bär ett väntande (osänt, ej kasserat) utkast får
    inget till — sändaren tar trådens senaste osända text, och två väntande
    utkast var precis felet 2026-10-08. Returnerar True när utkastet skapades.
    """
    if not isinstance(utkast, dict) or not str(utkast.get("body") or "").strip():
        return False
    trad = await storage.ensure_outreach_thread(tenant_id, prospect_id=prospect_id)
    if await storage.get_pending_outreach_message(tenant_id, str(trad["id"])):
        return False
    gate = utkast.get("gate_checks")
    if isinstance(gate, str):
        gate = json.loads(gate or "{}")
    gate = dict(gate or {})
    # Main skickar (scheduler.skickas_har): godkännandet gäller, men posten
    # ägs nu av main — samma omskrivning som första synken 2026-10-17.
    if gate.get("godkand_i") == "development":
        gate["godkand_i"] = "main"
    gate["importerad_fran"] = fran
    status = str(utkast.get("ko_status") or "")
    if status not in _UTKASTSTATUSAR:
        status = "awaiting_review"
    scheduled = None
    if utkast.get("scheduled_at"):
        try:
            scheduled = datetime.fromisoformat(str(utkast["scheduled_at"]))
        except ValueError:
            scheduled = None
    await storage.queue_outreach_message(
        tenant_id,
        thread_id=str(trad["id"]),
        body=str(utkast.get("body") or ""),
        subject=str(utkast.get("subject") or ""),
        humanizer_variant=str(utkast.get("humanizer_variant") or ""),
        scheduled_at=scheduled or datetime.now(timezone.utc),
        status=status,
        gate_checks=gate,
    )
    return True


async def _importera_prospekt(storage, tenant_id: str, post: dict[str, Any], fran: str) -> dict[str, Any]:
    """Ett markerat lead ur leadsvyn. Samma dedupnyckel som körningsimporten:
    bolagsnamnet — finns bolaget redan hos kunden i main är det flyttat, men
    ett utkast som saknas kompletteras (en äldre flytt bar inte utkasten)."""
    p = (post.get("prospekt") or [{}])[0]
    namn = str(p.get("company_name") or "").strip()
    if not namn:
        return {"ref_id": post.get("ref_id"), "resultat": "fel", "fel": "Leadet saknar bolagsnamn."}
    befintliga = {
        str(x.get("company_name") or "").casefold(): x
        for x in await storage.list_prospects(tenant_id, limit=_DEDUP_TAK)
    }
    fanns = befintliga.get(namn.casefold())
    if fanns is not None:
        if await _importera_utkast(storage, tenant_id, str(fanns["id"]), post.get("utkast"), fran):
            return {"ref_id": post.get("ref_id"), "resultat": "kompletterad", "id": fanns["id"], "utkast": 1}
        return {"ref_id": post.get("ref_id"), "resultat": "redan_flyttad"}
    profil = {
        f: p[f]
        for f in _PROSPEKTFALT
        if f not in ("company_name", "contact_name", "contact_email", "origin") and p.get(f) is not None
    }
    profil["importerad_fran"] = fran
    skapad = await storage.create_prospect(
        tenant_id, company_name=namn, contact_name=p.get("contact_name"),
        contact_email=p.get("contact_email"),
        origin=_skarp_origin(p.get("origin")),
        profil=profil,
    )
    # Bedömningen följer med, som i körningsflytten nedan: create_prospect tar
    # bara grundfälten, och leadet hade annars landat i main obedömt.
    bedomning = {f: p[f] for f in BEDOMNINGSFALT if p.get(f) is not None}
    if bedomning:
        await storage.spara_bedomning(tenant_id, skapad["id"], bedomning=bedomning)
    await _importera_utkast(storage, tenant_id, str(skapad["id"]), post.get("utkast"), fran)
    return {"ref_id": post.get("ref_id"), "resultat": "importerad", "id": skapad["id"]}


async def _importera_korning(storage, tenant_id: str, post: dict[str, Any], fran: str) -> dict[str, Any]:
    """En körning med sina prospekt och deras väntande utkast.

    En körning som redan finns (job_id) stannar inte vid "redan flyttad":
    prospekten och utkasten gås igenom ändå, och det en äldre flytt inte bar
    (utkast fanns inte i paketet före 2026-10-20) kompletteras. Därför går
    bulkflytten (scripts/flytta_korningar_till_main.py) att köra om säkert.
    """
    k = post.get("korning") or {}
    job_id = str(k.get("job_id") or post["ref_id"])
    fanns = await storage.get_leads_korning(tenant_id, job_id) is not None
    befintliga = {
        str(p.get("company_name") or "").casefold(): p
        for p in await storage.list_prospects(tenant_id, limit=_DEDUP_TAK)
    }
    nya = 0
    nya_utkast = 0
    for p in post.get("prospekt") or []:
        namn = str(p.get("company_name") or "").strip()
        if not namn:
            continue
        rad = befintliga.get(namn.casefold())
        if rad is None:
            profil = {f: p[f] for f in _PROSPEKTFALT if f not in ("company_name", "contact_name", "contact_email", "origin") and p.get(f) is not None}
            profil["importerad_fran"] = fran
            rad = await storage.create_prospect(
                tenant_id, company_name=namn, contact_name=p.get("contact_name"),
                contact_email=p.get("contact_email"),
                origin=_skarp_origin(p.get("origin")),
                profil=profil,
            )
            # Bedömningen följer med (2026-10-05): create_prospect tar bara
            # grundfälten, så nivå, poäng, motivering, kriterier, lägesbeskrivning
            # och webbrevisionen föll bort och leadet landade i main obedömt.
            bedomning = {f: p[f] for f in BEDOMNINGSFALT if p.get(f) is not None}
            if bedomning:
                await storage.spara_bedomning(tenant_id, rad["id"], bedomning=bedomning)
            befintliga[namn.casefold()] = rad
            nya += 1
        if await _importera_utkast(storage, tenant_id, str(rad["id"]), p.get("utkast"), fran):
            nya_utkast += 1
    if fanns and not nya and not nya_utkast:
        return {"ref_id": post["ref_id"], "resultat": "redan_flyttad"}
    if not fanns:
        await storage.set_leads_job_status(
            tenant_id, job_id=job_id, status=str(k.get("status") or "completed"), scope=str(k.get("scope") or "batch"),
            korning={**(k.get("korning") or {}), "importerad_fran": fran}, error=k.get("error"), is_test=bool(k.get("is_test")),
        )
    return {
        "ref_id": post["ref_id"],
        "resultat": "kompletterad" if fanns else "importerad",
        "prospekt": nya,
        "utkast": nya_utkast,
    }


async def _importera_lista(storage, tenant_id: str, post: dict[str, Any], fran: str) -> dict[str, Any]:
    """En leadslista med sina rader. Importeras skarp (is_test = false), se
    modulens docstring. Finns en lista med samma titel hos kunden är den flyttad."""
    lista = post.get("lista") or {}
    titel = str(lista.get("titel") or "").strip()
    if not titel:
        return {"ref_id": post.get("ref_id"), "resultat": "fel", "fel": "Listan saknar titel."}
    befintliga = {str(x.get("titel") or "").strip().casefold() for x in await storage.list_lead_lists(tenant_id, limit=500)}
    if titel.casefold() in befintliga:
        return {"ref_id": post.get("ref_id"), "resultat": "redan_flyttad"}
    sedda = await upptagna.hamta(storage, tenant_id)
    rader: list[dict[str, Any]] = []
    upptagna_bort = 0
    for rad in post.get("rader") or []:
        if upptagna.upptagen(sedda, rad.get("company_name"), rad.get("orgnr")):
            upptagna_bort += 1
            continue
        sedda |= upptagna.bolagsnycklar([rad])
        rader.append(rad)
    icp = lista.get("icp") if isinstance(lista.get("icp"), dict) else {}
    ny = await storage.create_lead_list(
        tenant_id,
        titel=titel,
        icp=icp,
        antal=max(1, min(int(lista.get("antal") or len(rader) or 1), 500)),
        is_test=False,
        kalla=str(lista.get("kalla") or "sok"),
        # Källistorna är developments id:n och finns inte i main.
        kallistor=None,
        kontaktfilter=lista.get("kontaktfilter"),
    )
    for rad in rader:
        await storage.add_lead_list_item(
            tenant_id, list_id=ny["id"], **{f: rad.get(f) for f in _LISTRADSFALT if rad.get(f) is not None}
        )
    await storage.set_lead_list_status(tenant_id, ny["id"], status=str(lista.get("status") or "klar"))
    await storage.log_platform_event(
        level="info",
        source="admin.flytt",
        message=f"Lista flyttad från {fran}: {titel} ({len(rader)} rader, {upptagna_bort} redan upptagna).",
        tenant_id=tenant_id,
        detail={"fran_lista": post.get("ref_id"), "ny_lista": ny["id"], "importerad_fran": fran},
    )
    return {
        "ref_id": post.get("ref_id"), "resultat": "importerad", "id": ny["id"],
        "rader": len(rader), "upptagna": upptagna_bort,
    }
