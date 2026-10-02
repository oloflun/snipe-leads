"""Leads Suite (plan del F, Fas 10): tidslinje, anteckningar, uppgifter,
sparade vyer och CSV-import ovanpå prospektregistret.

Egen modul och inte fler rader i leads.py: det här är CRM-ytan runt
prospektet, inte Iris körningar. Tidslinjen är ingen tabell — den komponeras
här ur det som redan finns (prospektet, statusloggen, mejltråden,
anteckningarna, uppgifterna), så den kan aldrig visa något annat än källorna.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..leads import crm_synk
from .deps import kraev_uuid, require_tenant

router = APIRouter()

#: Hur mycket av ett mejl tidslinjen visar. Hela tråden finns i inkorgen.
_MEJLUTDRAG = 300


class AnteckningRequest(BaseModel):
    model_config = {"extra": "forbid"}

    text: str = Field(..., min_length=1, max_length=4000)


class UppgiftRequest(BaseModel):
    model_config = {"extra": "forbid"}

    titel: str = Field(..., min_length=1, max_length=300)
    forfaller: date | None = None


class UppgiftPatchRequest(BaseModel):
    model_config = {"extra": "forbid"}

    klar: bool


class VyRequest(BaseModel):
    model_config = {"extra": "forbid"}

    namn: str = Field(..., min_length=1, max_length=100)
    filter: dict[str, Any] = Field(default_factory=dict)


class Importrad(BaseModel):
    """En CSV-rad efter kolumnmappningen i webbläsaren. `company_name` är
    valfritt HÄR med flit: en rad utan bolagsnamn ska räknas som överhoppad,
    inte fälla hela importen med 422."""

    company_name: str | None = Field(default=None, max_length=200)
    orgnr: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_role: str | None = Field(default=None, max_length=200)
    contact_email: str | None = Field(default=None, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=200)


class ImportRequest(BaseModel):
    titel: str = Field(..., min_length=1, max_length=200)
    rader: list[Importrad] = Field(..., min_length=1, max_length=2000)


async def _kraev_prospekt(storage, tenant_id: str, prospect_id: str) -> dict:
    kraev_uuid(prospect_id, "Prospektet")
    prospect = await storage.get_prospect(tenant_id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")
    return prospect


def _handelse(typ: str, nar: Any, rubrik: str, *, text: str | None = None,
              id: Any = None, klar: bool | None = None) -> dict[str, Any]:
    return {
        "typ": typ,
        "nar": nar.isoformat() if hasattr(nar, "isoformat") else nar,
        "rubrik": rubrik,
        "text": text,
        "id": str(id) if id is not None else None,
        "klar": klar,
    }


def _tidpunkt(nar: Any) -> datetime:
    t = datetime.fromisoformat(str(nar))
    # Naiva tider (äldre rader, testfixturer) tolkas som UTC — annars kan de
    # inte jämföras med resten och hela tidslinjen faller.
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


@router.get("/api/leads/prospects/{prospect_id}/tidslinje")
async def tidslinje(request: Request, prospect_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    """Allt som hänt med bolaget, nyast först. Statusrubriken bär råa
    statusnycklar (`fran → till`) — UI:t översätter, så tidslinjen följer
    språket utan en andra kopia av etiketterna här."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    prospect = await _kraev_prospekt(storage, tenant_id, prospect_id)

    handelser = [_handelse("skapad", prospect.get("created_at"), prospect.get("company_name") or "")]
    for rad in await storage.list_status_logg(tenant_id, prospect_id=prospect_id):
        rubrik = f"{rad['fran']} → {rad['till']}" if rad.get("fran") else str(rad["till"])
        handelser.append(_handelse("status", rad["created_at"], rubrik, id=rad["id"]))

    trad = await storage.find_outreach_thread(tenant_id, prospect_id=prospect_id)
    if trad:
        for m in await storage.list_outreach_messages(tenant_id, str(trad["id"])):
            nar = m.get("sent_at") or m.get("created_at")
            if not nar:
                continue  # osänt utkast: ingen händelse än, det bor i Mejlutkast
            handelser.append(
                _handelse(
                    "mejl_in" if m.get("direction") == "inbound" else "mejl_ut",
                    nar,
                    m.get("subject") or "",
                    text=(m.get("body") or "")[:_MEJLUTDRAG] or None,
                    id=m.get("id"),
                )
            )

    for rad in await storage.list_lead_notes(tenant_id, prospect_id):
        handelser.append(_handelse("anteckning", rad["created_at"], "", text=rad["text"], id=rad["id"]))
    for rad in await storage.list_lead_tasks(tenant_id, prospect_id=prospect_id):
        handelser.append(
            _handelse(
                "uppgift", rad["created_at"], rad["titel"],
                text=rad.get("forfaller"), id=rad["id"], klar=bool(rad.get("klar")),
            )
        )

    # reversed före den stabila sorteringen: vid lika tid kommer det som
    # lades till sist i listan (och därmed hände sist) först.
    handelser = sorted(reversed(handelser), key=lambda h: _tidpunkt(h["nar"]), reverse=True)
    return {"handelser": handelser}


@router.post("/api/leads/prospects/{prospect_id}/anteckningar", status_code=201)
async def ny_anteckning(
    request: Request, prospect_id: str, payload: AnteckningRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    prospect = await _kraev_prospekt(storage, tenant["tenant_id"], prospect_id)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Anteckningen är tom.")
    rad = await storage.add_lead_note(tenant["tenant_id"], prospect_id=prospect_id, text=text)
    asyncio.create_task(
        crm_synk.synka_prospekt(storage, tenant["tenant_id"], prospect, handelse="anteckning", text=text)
    )
    return {"anteckning": rad}


@router.post("/api/leads/prospects/{prospect_id}/uppgifter", status_code=201)
async def ny_uppgift(
    request: Request, prospect_id: str, payload: UppgiftRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    await _kraev_prospekt(storage, tenant["tenant_id"], prospect_id)
    titel = payload.titel.strip()
    if not titel:
        raise HTTPException(status_code=422, detail="Uppgiften saknar titel.")
    rad = await storage.add_lead_task(
        tenant["tenant_id"],
        prospect_id=prospect_id,
        titel=titel,
        forfaller=payload.forfaller.isoformat() if payload.forfaller else None,
    )
    return {"uppgift": rad}


@router.patch("/api/leads/uppgifter/{task_id}")
async def andra_uppgift(
    request: Request, task_id: str, payload: UppgiftPatchRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(task_id, "Uppgiften")
    rad = await request.app.state.storage.update_lead_task(tenant["tenant_id"], task_id, klar=payload.klar)
    if not rad:
        raise HTTPException(status_code=404, detail="Uppgiften finns inte.")
    return {"uppgift": rad}


@router.get("/api/leads/uppgifter")
async def lista_uppgifter(request: Request, oppna: bool = False, tenant: dict = Depends(require_tenant)) -> dict:
    return {
        "uppgifter": await request.app.state.storage.list_lead_tasks(tenant["tenant_id"], bara_oppna=oppna)
    }


def _vy(rad: dict) -> dict:
    return {k: rad.get(k) for k in ("id", "namn", "filter", "created_at")}


@router.get("/api/leads/vyer")
async def lista_vyer(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    return {"vyer": [_vy(r) for r in await request.app.state.storage.list_lead_views(tenant["tenant_id"])]}


@router.post("/api/leads/vyer", status_code=201)
async def ny_vy(request: Request, payload: VyRequest, tenant: dict = Depends(require_tenant)) -> dict:
    namn = payload.namn.strip()
    if not namn:
        raise HTTPException(status_code=422, detail="Vyn saknar namn.")
    rad = await request.app.state.storage.create_lead_view(tenant["tenant_id"], namn=namn, filter=payload.filter)
    return {"vy": _vy(rad)}


@router.delete("/api/leads/vyer/{view_id}", status_code=204)
async def radera_vy(request: Request, view_id: str, tenant: dict = Depends(require_tenant)) -> Response:
    kraev_uuid(view_id, "Vyn")
    if not await request.app.state.storage.delete_lead_view(tenant["tenant_id"], view_id):
        raise HTTPException(status_code=404, detail="Vyn finns inte.")
    return Response(status_code=204)


#: Importradens fält som listraden bär. `status` saknar kolumn på
#: lead_list_items och följer inte med; statusen sätts i Snipra efter flytten.
_IMPORTFALT = ("company_name", "orgnr", "contact_name", "contact_role", "contact_email", "contact_phone", "website")


@router.post("/api/leads/import", status_code=201)
async def importera(request: Request, payload: ImportRequest, tenant: dict = Depends(require_tenant)) -> dict:
    """CSV-import från ett annat CRM → en leadslista med `kalla='import'`.
    Ingen dedup mot registret här: Flytta till Iris (`till-iris`) gör den, på
    samma sätt som för varje annan lista."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    rader: list[dict[str, Any]] = []
    for rad in payload.rader:
        falt = {f: (str(getattr(rad, f) or "").strip() or None) for f in _IMPORTFALT}
        if falt["company_name"]:
            rader.append(falt)
    hoppade_over = len(payload.rader) - len(rader)
    if not rader:
        raise HTTPException(status_code=422, detail="Ingen rad hade ett bolagsnamn.")

    lista = await storage.create_lead_list(
        tenant_id,
        titel=payload.titel.strip(),
        icp={},
        # ponytail: antal är check-begränsat 1–200 (migration 060), samma tak
        # som kombinerade listor; item_count bär det riktiga antalet.
        antal=min(len(rader), 200),
        kalla="import",
    )
    for falt in rader:
        await storage.add_lead_list_item(tenant_id, list_id=lista["id"], **falt)
    await storage.set_lead_list_status(tenant_id, lista["id"], status="klar")
    lista["status"] = "klar"
    lista["item_count"] = len(rader)
    return {"list": lista, "antal": len(rader), "hoppade_over": hoppade_over}
