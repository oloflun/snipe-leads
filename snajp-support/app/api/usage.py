"""Tenant-scopad förbrukning: journalens siffror, med kundens egen nyckel.

Adminytan har haft per-tenant-förbrukning länge (GET /api/admin/usage), men
bara bakom master-nyckeln — kunden själv (och pilotens externa läsare) kunde
inte se vad agenten kostat. Den här routern svarar på SAMMA fråga skopat till
den egna tenanten: dagliga körningar och tokens för supportagenten, plus var
dygnsbudgeten står (app/budget.py).

Tokens, inte kronor: prislappen per miljon tokens bor i frontend
(lib/admin/halsa.ts) och är en uppskattning — backenden ska inte bära en
andra kopia av en siffra som ändras med leverantörens prislista.
"""

from fastapi import APIRouter, Depends, Query, Request

from ..budget import budget_for
from .deps import require_tenant

router = APIRouter()


@router.get("/api/usage")
async def usage(
    request: Request,
    tenant: dict = Depends(require_tenant),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]

    rad = await storage.get_tenant(tenant_id)
    slug = (rad or {}).get("slug") or ""

    return {
        "dagar": await storage.daily_support_usage(tenant_id, days=days),
        "budget": {
            # 0 = inget tak satt. Frontenden visar då ingen budgetrad alls
            # i stället för "0 av 0".
            "tak": budget_for(slug),
            "forbrukat_24h": await storage.sum_support_tokens(tenant_id, hours=24),
        },
    }
