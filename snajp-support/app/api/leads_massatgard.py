"""Massåtgärder i Iris-listan och Ta bort lista (Antons beställning 2026-10-07).

Verktygsraden i Leads › Översikt markerar leads och kör en åtgärd på alla.
Skapa utkast och Skapa om går genom `POST /api/leads/prospects/processa-om`
(leads.py), Skicka genom granskningens approve-väg. Här bor resten:

- `POST /api/leads/prospects/arkivera` — Arkivera och Återställ. Ett
  arkiverat lead är dolt, behåller historiken och står kvar i
  uteslutningsmängden, så nästa körning hämtar inte bolaget igen. Arkivering
  ställer in leadets väntande utskick och kasserar osända utkast, och
  send_guard (scheduler, spärr noll) stoppar varje utskick till ett arkiverat
  lead — ett godkännande från i går går inte ut efter beslutet.
- `POST /api/leads/prospects/radera` — Ta bort, bara för leads som aldrig
  kontaktats. Ett kontaktat lead raderas inte: utskicksloggen bär
  90-dagarsspärren och avregistreringarna, så det arkiveras i stället.
- `DELETE /api/leads/listor/{list_id}` — Ta bort lista. Raderna följer med
  (on delete cascade, 060). CRM-listor får också tas bort.

Egen modul och inte fler rader i leads.py, av samma skäl som leads_suite.py:
det här är CRM-handgrepp runt prospektregistret, inte Iris körningar.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..leads.scheduler import avbryt_utskick_for_prospekt
from .deps import kraev_uuid, require_tenant

router = APIRouter()

#: Samma tak som Skapa utkast (ProcessaOmRequest): listan visar upp till 500
#: leads, och en åtgärd körs på de markerade.
MAX_PER_ANROP = 500


def _giltiga(ids: list[str]) -> list[str]:
    """Id:n som går att slå upp. Ett felformat id är ett id som inte finns —
    Postgres hade kastat på `::uuid[]` och svarat 500 för hela anropet."""
    ut: list[str] = []
    for varde in ids:
        try:
            ut.append(str(uuid.UUID(str(varde))))
        except ValueError:
            continue
    return list(dict.fromkeys(ut))


class ArkiveraRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=MAX_PER_ANROP)
    arkivera: bool = True


class RaderaRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=MAX_PER_ANROP)


@router.post("/api/leads/prospects/arkivera")
async def arkivera_prospekt(
    request: Request, payload: ArkiveraRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Arkiverar (eller återställer, `arkivera=false`) de markerade leadsen."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    traffar = await storage.arkivera_prospekt(tenant_id, _giltiga(payload.ids), arkivera=payload.arkivera)
    installda = 0
    if payload.arkivera:
        for pid in traffar:
            installda += await avbryt_utskick_for_prospekt(storage, tenant_id, pid)
    return {"ids": traffar, "arkiverad": payload.arkivera, "installda_utskick": installda}


@router.post("/api/leads/prospects/radera")
async def radera_prospekt(
    request: Request, payload: RaderaRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Raderar de markerade leads som aldrig kontaktats. Svaret säger vilka
    som raderades och varför resten vägrades, så att vyn kan erbjuda Arkivera
    för de kontaktade."""
    storage = request.app.state.storage
    giltiga = _giltiga(payload.ids)
    utfall = await storage.radera_prospekt(tenant["tenant_id"], giltiga) if giltiga else {"raderade": [], "kontaktade": []}
    raderade = set(utfall["raderade"])
    kontaktade = set(utfall["kontaktade"])
    vagrade = [
        {"id": pid, "skal": "kontaktad" if pid in kontaktade else "finns_inte"}
        for pid in dict.fromkeys(str(i) for i in payload.ids)
        if pid not in raderade
    ]
    return {"raderade": sorted(raderade), "vagrade": vagrade}


@router.delete("/api/leads/listor/{list_id}")
async def ta_bort_lista(
    request: Request, list_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Tar bort en lista med alla dess rader. Bolagen i den blir lediga för
    nästa körning igen (app/leads/upptagna.py läser listraderna)."""
    kraev_uuid(list_id, "Listan")
    storage = request.app.state.storage
    lista = await storage.get_lead_list(tenant["tenant_id"], list_id)
    if not lista:
        raise HTTPException(status_code=404, detail="Listan finns inte.")
    # En lista som byggs har ett jobb som skriver rader i den; raderas den
    # under tiden faller jobbet på främmande nyckeln mitt i.
    if lista.get("status") in ("bestalld", "byggs"):
        raise HTTPException(status_code=409, detail="Listan byggs fortfarande. Ta bort den när den är klar.")
    if not await storage.delete_lead_list(tenant["tenant_id"], list_id):
        raise HTTPException(status_code=404, detail="Listan finns inte.")
    return {"id": list_id, "raderad": True}
