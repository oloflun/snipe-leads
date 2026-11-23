"""Webbpoolens bakåtfyllnad, bakom master-nyckeln (Antons beställning 2026-11-22).

Alla kunders gamla leads och listrader med webbplats bedöms och fördelas till
webbyråerna. Det gäller också de som fick nivån okand medan
ScrapeGraph-krediten var slut. Startas bara här, aldrig av en körning, och
torrkör som standard. Kreditkontrollen vägrar starta när ScrapeGraphs saldo
inte räcker. Läget räknas ur poolen, så det finns kvar efter en omstart.
Själva logiken finns i app/leads/webbpool.py (bakatfyll).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..leads import webbpool
from .deps import require_master_key

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])


class BakatfyllRequest(BaseModel):
    apply: bool = False
    max_bedom: int | None = None
    utan_kreditkontroll: bool = False


@router.get("/webbpool/bakatfyll")
async def bakatfyll_lage(request: Request) -> dict:
    lage = await webbpool.bakatfyll_lage(request.app.state.storage)
    lage["krediter_kvar"] = webbpool.scrapegraph_krediter()
    return lage


@router.post("/webbpool/bakatfyll")
async def bakatfyll(request: Request, payload: BakatfyllRequest) -> dict:
    storage = request.app.state.storage
    svar = await webbpool.bakatfyll(
        storage, apply=payload.apply, max_bedom=payload.max_bedom,
        utan_kreditkontroll=payload.utan_kreditkontroll,
    )
    if svar.get("startad"):
        await storage.log_platform_event(
            level="info", source="admin.webbpool_bakatfyll",
            message=f"Webbpoolens bakåtfyllnad startad: {svar['ska_bedomas']} sajter.",
            detail={"krediter_kvar": svar.get("krediter_kvar"), "max_bedom": payload.max_bedom},
        )
    return svar
