"""Leads › Uppföljningar och bolagssökningen (Antons beställning 2026-11-22).

## Uppföljningarna

"Det finns inget gränssnitt eller insikt i när återkopplingsmejl skapas och
vart de hamnar": uppföljningarna (app/leads/follow_up_generator.py) skrivs av
svepet och står i samma granskningskö som körningarnas första mejl, utan att
gå att skilja ut. Här står de för sig, per lead:

* vantar     en uppföljning väntar på granskning (nummer n av 4)
* skrivs     Iris skriver en uppföljning just nu (utkastjobbet i liggaren)
* forfallna  dags för nästa uppföljning, men ingen är skriven än
* kommande   nästa uppföljning och när den blir aktuell
* skickade   uppföljningar som gått ut de senaste 30 dagarna
* fel        en uppföljning som inte gick att skriva, med skälet

Allt härleds ur trådarna, kön och jobbliggaren varje gång listan hämtas;
inget nytt lagras. Förloppet för Skapa uppföljning är jobbliggaren
(`skrivs`), så det står kvar efter en omladdning.

`POST /api/leads/uppfoljningar/skapa` skriver en uppföljning nu för de
markerade leadsen, genom samma jobbväg som Skapa om utkast
(api/leads._run_uppfoljningsjobb → follow_up_generator.skriv_om_uppfoljning):
samma kedja, samma grindar, alltid till granskning.

## Bolagssökningen

`GET /api/leads/sok?q=` hittar ett bolag bland ALLA kundens leads, också de
som fått mejl, svarat eller arkiverats (Iris-listan visar bara de aktiva), på
namn, kontakt, e-post, webbplats eller organisationsnummer. Träffen öppnar
leadets låda: profilen, utkastet och tidslinjen med tidigare utskick.
Webbplatsbedömningen följer inte med (projektregeln 2026-10-08).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..leads import automation as automationsregler
from ..leads.follow_up_generator import _AVSLUTADE, FOLLOW_UP_DELAYS, MAX_OUTBOUND
from .deps import require_tenant

router = APIRouter()

#: Uppföljningar per tråd (första mejlet räknas inte): 1–4, där 4 är breakup.
ANTAL_UPPFOLJNINGAR = MAX_OUTBOUND - 1

#: Hur långt bak Skickade visar.
SKICKADE_DAGAR = 30


class SkapaRequest(BaseModel):
    model_config = {"extra": "forbid"}

    prospect_ids: list[str] = Field(..., min_length=1, max_length=200)


def _tid(varde: Any) -> datetime | None:
    if varde in (None, ""):
        return None
    t = varde if isinstance(varde, datetime) else datetime.fromisoformat(str(varde))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _iso(varde: Any) -> Any:
    return varde.isoformat() if hasattr(varde, "isoformat") else varde


def _bas(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "prospect_id": str(t["prospect_id"]),
        "thread_id": str(t["id"]),
        "company_name": t.get("company_name"),
        "contact_email": t.get("contact_email"),
        "skickade": int(t.get("outbound_sent_count") or 0),
        "senast_skickat": _iso(t.get("last_outbound_sent_at")),
        "av": ANTAL_UPPFOLJNINGAR,
    }


def fordela(
    tradar: list[dict[str, Any]],
    *,
    lagen: dict[str, dict[str, Any]],
    utkastjobb: dict[str, dict[str, Any]],
    automation: dict[str, Any] | None,
    now: datetime,
) -> dict[str, list[dict[str, Any]]]:
    """Ren funktion: trådarna i uppföljningsflikens fack. Samma policy som
    svepet (follow_up_generator.trad_som_ar_forfallna) för när nästa
    uppföljning är förfallen, så att fliken och svepet aldrig är oense."""
    regler = automationsregler.normalisera(automation)
    fack: dict[str, list[dict[str, Any]]] = {k: [] for k in ("vantar", "skrivs", "forfallna", "kommande", "fel")}
    for t in tradar:
        skickade = int(t.get("outbound_sent_count") or 0)
        if skickade < 1 or t.get("origin") == "example" or not t.get("prospect_id"):
            continue
        pid = str(t["prospect_id"])
        rad = _bas(t)
        lage = lagen.get(pid) or {}
        jobb = utkastjobb.get(pid) or {}
        if jobb.get("status") in ("queued", "processing"):
            fack["skrivs"].append({**rad, "nummer": min(skickade, ANTAL_UPPFOLJNINGAR)})
            continue
        avslutad = bool(t.get("last_inbound_at")) or t.get("prospect_status") in _AVSLUTADE or bool(t.get("arkiverad_at"))
        if int(lage.get("antal_osanda") or 0) > 0 and not avslutad:
            fack["vantar"].append({
                **rad, "nummer": min(skickade, ANTAL_UPPFOLJNINGAR),
                "queue_item_id": lage.get("queue_item_id"), "ko_status": lage.get("ko_status"),
            })
            continue
        if avslutad or skickade >= MAX_OUTBOUND:
            continue
        if jobb.get("status") == "failed" and jobb.get("error"):
            fack["fel"].append({**rad, "nummer": skickade, "fel": jobb.get("error")})
        dagar = regler["per_typ"][automationsregler.typ_av(t.get("origin"))]["uppfoljning_dagar"]
        senast = _tid(t.get("last_outbound_sent_at"))
        if not senast:
            continue
        vanta = timedelta(days=dagar) if skickade == 1 else FOLLOW_UP_DELAYS[skickade]
        nasta = senast + vanta
        post = {**rad, "nummer": skickade, "nasta": nasta.isoformat(), "avstangd": dagar == 0}
        (fack["forfallna"] if dagar and nasta <= now else fack["kommande"]).append(post)
    fack["forfallna"].sort(key=lambda r: r["nasta"])
    fack["kommande"].sort(key=lambda r: (r["avstangd"], r["nasta"]))
    return fack


def skickade_uppfoljningar(
    skickat: list[dict[str, Any]], tradar: dict[str, dict[str, Any]], *, now: datetime
) -> list[dict[str, Any]]:
    """Uppföljningar som gått ut, nyast först: varje skickat mejl i en tråd
    utom det första. Numret räknas ur trådens antal skickade, så att ett
    första mejl utanför fönstret (list_skickade tar de senaste 500) inte
    gör den andra uppföljningen till den första."""
    per_trad: dict[str, list[dict[str, Any]]] = {}
    for m in skickat:
        if m.get("thread_id"):
            per_trad.setdefault(str(m["thread_id"]), []).append(m)
    grans = now - timedelta(days=SKICKADE_DAGAR)
    ut = []
    for tid, mejl in per_trad.items():
        mejl.sort(key=lambda m: _tid(m.get("sent_at")) or now)
        totalt = int((tradar.get(tid) or {}).get("outbound_sent_count") or len(mejl))
        forskjutning = totalt - len(mejl)
        for i, m in enumerate(mejl):
            nummer = forskjutning + i
            skickad = _tid(m.get("sent_at"))
            if nummer < 1 or not skickad or skickad < grans:
                continue
            ut.append({
                "message_id": str(m["id"]), "thread_id": tid, "prospect_id": str(m.get("prospect_id") or ""),
                "company_name": m.get("company_name"), "contact_email": m.get("prospect_email"),
                "subject": m.get("subject"), "body": m.get("body") or "", "skickat_at": _iso(m.get("sent_at")),
                "nummer": min(nummer, ANTAL_UPPFOLJNINGAR), "av": ANTAL_UPPFOLJNINGAR,
                "svarat": bool((tradar.get(tid) or {}).get("last_inbound_at")),
            })
    return sorted(ut, key=lambda r: r["skickat_at"] or "", reverse=True)


@router.get("/api/leads/uppfoljningar")
async def uppfoljningar(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    import asyncio

    from ..config import get_settings

    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    now = datetime.now(timezone.utc)
    tradar, lagen, utkastjobb, installningar, skickat = await asyncio.gather(
        storage.list_outreach_threads(tenant_id),
        storage.utkast_lagen(tenant_id),
        storage.utkastjobb_lage(tenant_id),
        storage.get_agent_settings(tenant_id, agent_type="leads"),
        storage.list_skickade(tenant_id, limit=500),
    )
    fack = fordela(tradar, lagen=lagen, utkastjobb=utkastjobb, automation=installningar.get("automation"), now=now)
    # Texten bara för de väntande: listan över alla trådar ska inte bära mejlkroppar.
    if fack["vantar"]:
        texter = await storage.utkast_lagen(tenant_id, med_text=True, bara=[r["prospect_id"] for r in fack["vantar"]])
        for r in fack["vantar"]:
            t = texter.get(r["prospect_id"]) or {}
            r.update(subject=t.get("subject"), body=t.get("body") or "", message_id=_iso(t.get("message_id")))
    per_trad = {str(t["id"]): t for t in tradar}
    fack["skickade"] = skickade_uppfoljningar(skickat, per_trad, now=now)[:50]
    return {
        **fack,
        "antal": {k: len(v) for k, v in fack.items()},
        # Svepet skriver förfallna uppföljningar varje timme där
        # schemaläggaren går (scheduler.sweep_follow_ups).
        "automatiskt": get_settings().send_queue_poll_seconds > 0,
    }


@router.post("/api/leads/uppfoljningar/skapa", status_code=202)
async def skapa(request: Request, payload: SkapaRequest, tenant: dict = Depends(require_tenant)) -> dict:
    """Skriver en uppföljning nu för de markerade leadsen, oavsett när nästa
    var planerad. Hoppar över (med skäl) leads utan skickat mejl, som svarat
    eller avslutats, vars sekvens är slut, som redan har en uppföljning som
    väntar, eller där en redan skrivs."""
    from ..leads.follow_up_generator import uppfoljningstrad
    from .leads import _kraev_leads_budget, _lagg_prospektjobb, _require_live_llm

    _require_live_llm()
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    await _kraev_leads_budget(storage, tenant_id)
    lagen = await storage.utkast_lagen(tenant_id)
    jobb = await storage.utkastjobb_lage(tenant_id)
    hoppade: dict[str, list[str]] = {}
    valda: list[dict] = []
    for pid in dict.fromkeys(payload.prospect_ids):
        try:
            uuid.UUID(str(pid))
        except ValueError:
            continue
        skal = None
        trad = await uppfoljningstrad(storage, tenant_id, pid)
        if trad is None:
            skal = "inget_skickat"
        elif trad.get("last_inbound_at") or trad.get("prospect_status") in _AVSLUTADE or trad.get("arkiverad_at"):
            skal = "avslutad"
        elif int(trad.get("outbound_sent_count") or 0) >= MAX_OUTBOUND:
            skal = "sekvensen_klar"
        elif (jobb.get(pid) or {}).get("status") in ("queued", "processing"):
            skal = "skrivs_redan"
        elif int((lagen.get(pid) or {}).get("antal_osanda") or 0) > 0:
            skal = "har_utkast"
        if skal:
            hoppade.setdefault(skal, []).append(pid)
        else:
            valda.append({"id": pid})
    if not valda:
        return {"count": 0, "jobs": [], "hoppade": hoppade}
    jobs = await _lagg_prospektjobb(
        request.app.state, tenant, valda, scope="utkast", overrides=None, is_test=False,
        limit=len(valda), struktur=None,
    )
    return {"count": len(jobs), "jobs": jobs, "hoppade": hoppade}


@router.get("/api/leads/sok")
async def sok(request: Request, q: str = "", tenant: dict = Depends(require_tenant)) -> dict:
    """Bolagssökningen: alla kundens leads, på namn, kontakt, e-post,
    webbplats eller organisationsnummer. Högst 20 träffar, bäst först."""
    fraga = " ".join(q.lower().split())
    if len(fraga) < 2:
        return {"traffar": []}
    if len(fraga) > 100:
        raise HTTPException(status_code=422, detail="Sökningen får vara högst 100 tecken.")
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    kolumner = ("company_name", "contact_name", "contact_email", "contact_phone", "website", "orgnr", "ort",
                "status", "origin", "arkiverad_at", "created_at")
    # ponytail: hela kundens leads läses och filtreras här, som samtalslistorna
    # (leads_suite._samtalsunderlag); ett index med trigram när en kund har
    # tiotusentals.
    prospekter = await storage.list_prospects(tenant_id, limit=20_000, kolumner=kolumner)
    siffror = "".join(c for c in fraga if c.isdigit())
    traffar = []
    for p in prospekter:
        if p.get("origin") == "example":
            continue
        namn = str(p.get("company_name") or "").lower()
        falt = " ".join(str(p.get(k) or "").lower() for k in ("contact_name", "contact_email", "website", "ort"))
        orgnr = "".join(c for c in str(p.get("orgnr") or "") if c.isdigit())
        if namn.startswith(fraga):
            rang = 0
        elif fraga in namn:
            rang = 1
        elif fraga in falt or (len(siffror) >= 4 and siffror in orgnr):
            rang = 2
        else:
            continue
        traffar.append((rang, namn, p))
    traffar.sort(key=lambda t: (t[0], t[1]))
    trader = {}
    if traffar:
        for t in await storage.list_outreach_threads(tenant_id):
            if t.get("prospect_id"):
                trader[str(t["prospect_id"])] = t
    ut = []
    for _, _, p in traffar[:20]:
        t = trader.get(str(p["id"])) or {}
        ut.append({
            "id": str(p["id"]), "company_name": p.get("company_name"), "ort": p.get("ort"),
            "contact_name": p.get("contact_name"), "contact_email": p.get("contact_email"),
            "orgnr": p.get("orgnr"), "status": p.get("status"), "arkiverad": bool(p.get("arkiverad_at")),
            "skickade": int(t.get("outbound_sent_count") or 0),
            "senast_skickat": _iso(t.get("last_outbound_sent_at")),
            "thread_id": str(t["id"]) if t.get("id") else None,
            "svarat": bool(t.get("last_inbound_at")),
        })
    return {"traffar": ut}
