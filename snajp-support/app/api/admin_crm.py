"""Supportens sida av Snajp CRM: synkens felrapporter (migration 163).

Antons svar 2026-11-26: kunden ser felen i enkla ord, och hela rapporten med
alla koder blir ett supportärende. CRM:et lägger fram rapporten här, och
supportsystemet hämtar den och svarar med ärendets nummer.

    GET  /api/admin/crm/supportrapporter                 listan, nyast först
    GET  /api/admin/crm/supportrapporter/{kund}/{körning} hela rapporten
    POST /api/admin/crm/supportrapporter/{kund}/{körning}/arende   {"nummer": "F-ABCD"}

Numret visas sedan för kunden på körningen (CRM › Synk), så att kunden kan
hänvisa till det.

Samma grind som övriga /api/admin-vägar: `require_master_key` på routern, och
därmed åtkomstloggen (adminlogg.py, INV-SEC-013). Rapporten bär inga värden
som inte gick att tolka, bara deras form (app/crm/supportrapport.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..crm import lagring, supportrapport
from .deps import kraev_uuid, require_master_key

router = APIRouter(prefix="/api/admin/crm", dependencies=[Depends(require_master_key)])


class Arendenummer(BaseModel):
    nummer: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _#\-]*$")


@router.get("/supportrapporter")
async def lista_supportrapporter(
    request: Request,
    utan_arende: bool = Query(False, description="Bara rapporter som inget ärende tagit emot än."),
    limit: int = Query(200, ge=1, le=500),
) -> dict:
    return {"rapporter": await supportrapport.lista(request.app.state.storage, bara_utan_arende=utan_arende,
                                                    limit=limit)}


async def _korning(request: Request, tenant_id: str, korning_id: str) -> dict:
    korning = await lagring.hamta_korning(request.app.state.storage, kraev_uuid(tenant_id, "Kunden"),
                                          kraev_uuid(korning_id, "Körningen"))
    if korning is None or not korning.get("support_lamnad_at"):
        raise HTTPException(status_code=404, detail="Rapporten finns inte.")
    return korning


@router.get("/supportrapporter/{tenant_id}/{korning_id}")
async def hamta_supportrapport(request: Request, tenant_id: str, korning_id: str) -> dict:
    korning = await _korning(request, tenant_id, korning_id)
    return {"tenant_id": tenant_id, "korning_id": korning_id, "lamnad_at": korning["support_lamnad_at"],
            "arende": korning.get("support_arende"), "rapport": korning.get("supportrapport") or {}}


@router.post("/supportrapporter/{tenant_id}/{korning_id}/arende")
async def satt_arende(request: Request, tenant_id: str, korning_id: str, kropp: Arendenummer) -> dict:
    """Supportsystemet har tagit emot rapporten. Numret visas för kunden."""
    await _korning(request, tenant_id, korning_id)
    ny = await supportrapport.satt_arende(request.app.state.storage, tenant_id, korning_id, kropp.nummer.strip())
    return {"tenant_id": tenant_id, "korning_id": korning_id, "arende": (ny or {}).get("support_arende")}
