"""Utkastsvepet: hälsnings- och signaturreglerna på alla osända leads-utkast.

Sebbe 2026-10-12: alla befintliga utskick ska uppdateras efter de senaste
reglerna (hälsningsraden i app/leads/halsning.py, signaturen med loggan),
inte bara nya. Köläsningens lata fix når bara utkast i granskningskön
(awaiting_review) och bara när någon öppnar just den kundens kö — svepet tar
resten: godkända som väntar på sändfönstret, stoppade, och kunder vars kö
ingen öppnat.

Samma pass som köningen, köläsningen och godkännandet kör
(halsning.normalisera_tenantens_utkast). Idempotent: andra svepet rättar
noll. Skickade mejl rörs aldrig. Ligger inte i admin.py: den filen skriver
inte (se dess docstring).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from ..leads.halsning import normalisera_tenantens_utkast
from .deps import require_master_key

logger = logging.getLogger("snajp-support.admin.utkastsvep")

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])


@router.post("/leads/normalisera-utkast")
async def normalisera_utkast_alla_tenants(request: Request) -> dict:
    storage = request.app.state.storage
    ut: dict[str, dict[str, int]] = {}
    for tenant in await storage.list_tenants():
        try:
            resultat = await normalisera_tenantens_utkast(storage, str(tenant["id"]))
        except Exception:  # noqa: BLE001 — en kunds fel ska inte stoppa resten
            logger.exception("Utkastsvepet föll för %s", tenant.get("slug"))
            resultat = {"fel": 1}
        if any(resultat.values()):
            ut[str(tenant.get("slug") or tenant["id"])] = resultat
    return {"tenants": ut}
