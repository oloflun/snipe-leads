"""API-nyckel-autentisering (X-API-Key) — multi-tenant.

Varje nyckel mappar till exakt en tenant:
- Demo-nyckeln (config) → default-tenanten Nordlys Handel.
- snajp_live_-nycklar → sha256-uppslag i lagringen → nyckelns tenant.
- Master-nyckeln är administrativ (skapa tenants/nycklar) och har INGEN tenant —
  den kan därför inte användas mot kunddata-endpoints.
"""

from uuid import UUID

from fastapi import Header, HTTPException, Request

from ..config import DEFAULT_TENANT_ID, DEFAULT_TENANT_NAME, get_settings


def kraev_uuid(varde: str, vad: str) -> str:
    """Ett id ur sökvägen som GÅR att slå upp — annars 404, aldrig 500.

    Postgres kastar på `'inte-ett-uuid'::uuid`, och utan den här kontrollen
    bubblar det upp som ett ohanterat undantag. Uppmätt mot dev-deployen:
    /api/tickets/inte-ett-uuid och /api/customers/inte-ett-uuid/history svarade
    båda 500, liksom /api/leads/prospects/{id}.

    Ett 500 är fel svar på ett felformat id av två skäl. Det säger att VI
    gick sönder när det var anroparen som skrev fel. Och i webbappen faller
    felet ur "finns inte"-grenen och landar i den allmänna felrutan, så
    användaren får "Kunde inte hämta bolaget (status 500)" i stället för
    "Bolaget finns inte".

    404 och inte 422, av samma skäl som endpointsen redan svarar 404 på ett
    okänt id: ett felformat id och ett id som inte finns ska inte gå att
    skilja åt utifrån. Annars blir svaret en uppräkningskanal.
    """
    try:
        UUID(varde)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail=f"{vad} finns inte.") from None
    return varde


async def require_api_key(
    request: Request, x_api_key: str | None = Header(default=None)
) -> dict:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key saknas.")
    settings = get_settings()
    if x_api_key == settings.snajp_demo_api_key:
        return {"tenant_id": DEFAULT_TENANT_ID, "tenant_name": DEFAULT_TENANT_NAME, "master": False}
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
