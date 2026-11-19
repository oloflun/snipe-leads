"""Gallringens insyn för plattformsadmin: policy per kund och vad som gallrats.

Projektregeln (2026-10-10) är att varje bakgrundsfunktion går att följa, och
att utfallet finns kvar efter en omladdning. Gallringen körs av api-tjänsten
en gång per dygn (app/jobs/gallring.py); utfallet står i ss_gallringslogg
(migration 119), och den här vägen läser det.

Bara läsning. Att sätta en policy och att radera är ägarens beslut och görs
med scripts/gallra.py, inte härifrån: en knapp som raderade kunddata hade
behövt samma torrkörning och samma andra blick som skriptet redan kräver.

Svaret bär inga personuppgifter: antal per tabell, tider och kundens slug.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..config import get_settings
from .deps import kraev_uuid, require_master_key

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])


@router.get("/gallring")
async def gallring_oversikt(request: Request, limit: int = 50) -> dict:
    """Inställningen, de senaste dygnens körningar, varje kunds policy och
    senaste skarpa körning, och de senaste loggraderna."""
    storage = request.app.state.storage
    settings = get_settings()
    limit = max(1, min(limit, 500))
    return {
        "installning": {
            "aktiv": settings.gallring_aktiv,
            "tak": settings.gallring_tak,
            "timme": settings.gallring_timme,
        },
        "spegel": bool(await storage.spegel_info()),
        "korningar": await storage.list_gallringskorningar(limit=14),
        "kunder": await storage.list_gallringspolicyer(),
        "logg": await storage.list_gallringslogg(limit=limit),
    }


@router.get("/tenants/{tenant_id}/gallring")
async def gallring_for_kund(request: Request, tenant_id: str, limit: int = 50) -> dict:
    """En kunds gallringslogg, nyast först."""
    kraev_uuid(tenant_id, "Kunden")
    storage = request.app.state.storage
    limit = max(1, min(limit, 500))
    policy = next(
        (k for k in await storage.list_gallringspolicyer() if k.get("tenant_id") == tenant_id),
        None,
    )
    return {
        "policy": policy,
        "logg": await storage.list_gallringslogg(tenant_id=tenant_id, limit=limit),
    }
