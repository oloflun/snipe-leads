"""Admin master control — läsning över alla kunder.

Varför en egen router: `require_tenant` avvisar master-nyckeln mot kunddata
med 403 (deps.py). Det är rätt designat — en administrativ nyckel ska inte
kunna smyga in som en kund — men det betyder att överblicken behöver en egen
väg. **Allt här ligger bakom `require_master_key`.**

Ingen endpoint här skriver. En admin-vy som kan ändra kunddata är en vy som
förr eller senare gör det av misstag, och den enda ändring vi faktiskt
behöver (autonominivå, ICP) gör kunden själv i sin egen vy.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from .deps import require_master_key

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])


@router.get("/tenants")
async def list_tenants(request: Request) -> dict:
    return {"tenants": await request.app.state.storage.list_tenants_with_stats()}


@router.get("/tenants/{tenant_id}/runs")
async def list_tenant_runs(request: Request, tenant_id: str, limit: int = 50) -> dict:
    runs = await request.app.state.storage.list_agent_runs_all(
        tenant_id=tenant_id, limit=min(limit, 200)
    )
    return {"runs": runs}


@router.get("/runs")
async def list_runs(
    request: Request,
    tenant_id: str | None = None,
    agent_type: str | None = None,
    limit: int = 50,
) -> dict:
    runs = await request.app.state.storage.list_agent_runs_all(
        tenant_id=tenant_id, agent_type=agent_type, limit=min(limit, 200)
    )
    return {"runs": runs}


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: str) -> dict:
    run = await request.app.state.storage.get_agent_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Körningen finns inte.")
    return {"run": run}


@router.get("/events")
async def list_events(
    request: Request,
    level: str | None = None,
    tenant_id: str | None = None,
    limit: int = 100,
) -> dict:
    """Notiscentret. Fel över alla kunder, senast först."""
    events = await request.app.state.storage.list_platform_events(
        level=level, tenant_id=tenant_id, limit=min(limit, 500)
    )
    return {"events": events}


@router.get("/tenants/{tenant_id}/inbox")
async def tenant_inbox(request: Request, tenant_id: str, limit: int = 50) -> dict:
    return {"emails": await request.app.state.storage.list_emails(tenant_id, limit=min(limit, 200))}


@router.get("/tenants/{tenant_id}/drafts")
async def tenant_drafts(request: Request, tenant_id: str, limit: int = 50) -> dict:
    """Kundens utkast. Går via samma granskningskö som kunden själv ser —
    admin har ingen egen, andra sanning om vad som väntar."""
    return {
        "queue": await request.app.state.storage.list_review_queue(
            tenant_id, limit=min(limit, 200)
        )
    }


@router.get("/usage")
async def usage(request: Request) -> dict:
    """Förbrukning per kund. Samma siffror som /tenants, men utan
    ärendemängden — det här är fakturerings- och kostnadsvyn, och att blanda
    in aktivitetsmått där gör det oklart vad man tittar på."""
    tenants = await request.app.state.storage.list_tenants_with_stats()
    return {
        "usage": [
            {
                "tenant_id": t["id"],
                "slug": t.get("slug"),
                "name": t.get("name"),
                "runs": t.get("runs", 0),
                "tokens_in": t.get("tokens_in", 0),
                "tokens_out": t.get("tokens_out", 0),
                "last_activity": t.get("last_activity"),
            }
            for t in tenants
        ]
    }
