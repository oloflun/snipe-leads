"""Testkund → riktig kund, bakom master-nyckeln.

Ligger inte i admin.py: den filen skriver inte. Se admin_profil.py för
samma uppdelning.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..tenants.konvertera import kora
from .deps import require_master_key

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])


class KonverteraRequest(BaseModel):
    fran: str = Field(..., min_length=8, max_length=80)
    till: str = Field(..., min_length=1, max_length=80)
    apply: bool = False
    prospekt: list[str] = Field(default_factory=list)


@router.post("/konvertera")
async def konvertera_testkund(request: Request, payload: KonverteraRequest) -> dict:
    """Torrkör som default. apply=true skriver över målets konfiguration."""
    rapport = await kora(
        request.app.state.storage,
        fran=payload.fran.strip(),
        till=payload.till.strip(),
        apply=payload.apply,
        prospect_ids=payload.prospekt,
    )
    if not rapport.get("ok"):
        raise HTTPException(status_code=422, detail=rapport.get("fel") or "Konverteringen avvisades.")
    if payload.apply:
        await request.app.state.storage.log_platform_event(
            level="info",
            source="admin.konvertera",
            message=f"Testkund {payload.fran} kopierades till {payload.till}.",
            detail={"fran": payload.fran, "till": payload.till, "prospekt": payload.prospekt},
        )
    return {"rapport": rapport}
