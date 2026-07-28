"""API-nyckel-autentisering (X-API-Key) — multi-tenant.

Varje nyckel mappar till exakt en tenant:
- Demo-nyckeln (config) → default-tenanten Nordlys Handel.
- snajp_live_-nycklar → sha256-uppslag i lagringen → nyckelns tenant.
- Master-nyckeln är administrativ (skapa tenants/nycklar) och har INGEN tenant —
  den kan därför inte användas mot kunddata-endpoints.
"""

from fastapi import Header, HTTPException, Request

from ..config import (
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
    PILOT_TENANT_ID,
    get_settings,
)


async def require_api_key(
    request: Request, x_api_key: str | None = Header(default=None)
) -> dict:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key saknas.")
    settings = get_settings()
    if x_api_key == settings.snajp_demo_api_key:
        return {"tenant_id": DEFAULT_TENANT_ID, "tenant_name": DEFAULT_TENANT_NAME, "master": False}
    if settings.snajp_pilot_api_key and x_api_key == settings.snajp_pilot_api_key:
        return {
            "tenant_id": PILOT_TENANT_ID,
            "tenant_name": settings.pilot_tenant_name,
            "master": False,
        }
    if x_api_key == settings.snajp_master_api_key:
        return {"tenant_id": None, "tenant_name": "master", "master": True}
    record = await request.app.state.storage.validate_api_key(x_api_key)
    if record:
        return {
            "tenant_id": record["tenant_id"],
            "tenant_name": record["tenant_name"],
            "master": False,
        }
    raise HTTPException(status_code=401, detail="Ogiltig API-nyckel.")


async def require_tenant(
    request: Request, x_api_key: str | None = Header(default=None)
) -> dict:
    """Nyckel med tenant-koppling — krävs för alla kunddata-endpoints."""
    tenant = await require_api_key(request, x_api_key)
    if not tenant["tenant_id"]:
        raise HTTPException(
            status_code=403,
            detail="Master-nyckeln är administrativ och kan inte användas mot kunddata.",
        )
    return tenant


async def require_master_key(
    request: Request, x_api_key: str | None = Header(default=None)
) -> dict:
    tenant = await require_api_key(request, x_api_key)
    if not tenant["master"]:
        raise HTTPException(status_code=403, detail="Kräver master-nyckel.")
    return tenant
