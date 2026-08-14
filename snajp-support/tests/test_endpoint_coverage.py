"""Ingen endpoint får glömmas bort i multi-tenancy-arbetet.

Testerna härleder listan ur appens OpenAPI-schema i stället för en handskriven
lista. Lägger någon till en ny endpoint utan tenant-skydd faller de här testerna
utan att någon behöver komma ihåg att uppdatera dem.

Två egenskaper kontrolleras för VARJE /api-endpoint:
  1. Utan nyckel → 401. Ingen kunddata får nås anonymt.
  2. Med master-nyckeln → aldrig 200. Master är administrativ och ska inte kunna
     läsa eller skriva kunddata; bara de uttryckligt administrativa vägarna
     svarar något annat än 403.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()
MASTER_KEY = settings.snajp_master_api_key

# Avsiktligt publika probes — de avslöjar ingen kunddata.
PUBLIC_PATHS = {"/health", "/health/live", "/health/ready"}

# Endpoints som ÄR administrativa och därför ska fungera med master-nyckeln.
MASTER_ENDPOINTS = {("POST", "/api/keys")}

DUMMY_ID = "00000000-0000-4000-a000-0000000000ff"


def _endpoints() -> list[tuple[str, str]]:
    spec = app.openapi()
    found = []
    for path, operations in spec["paths"].items():
        if path in PUBLIC_PATHS:
            continue
        for method in operations:
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                found.append((method.upper(), path))
    assert found, "Hittade inga endpoints i OpenAPI-schemat."
    return sorted(found)


ENDPOINTS = _endpoints()


def _concrete(path: str) -> str:
    """Byter ut {parametrar} mot ett id som inte finns hos någon tenant."""
    out = []
    for segment in path.split("/"):
        out.append(DUMMY_ID if segment.startswith("{") else segment)
    return "/".join(out)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _call(client, method: str, path: str, headers: dict):
    # Tomt men giltigt JSON-objekt räcker: auth-kontrollen sker före validering,
    # så ett 422 här skulle betyda att skyddet INTE höll.
    return await client.request(method, _concrete(path), headers=headers, json={})


@pytest.mark.anyio
@pytest.mark.parametrize("method,path", ENDPOINTS)
async def test_endpoint_requires_api_key(method, path):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await _call(client, method, path, {})
    assert response.status_code == 401, (
        f"{method} {path} svarade {response.status_code} utan nyckel — "
        "endpointen saknar tenant-skydd."
    )


@pytest.mark.anyio
@pytest.mark.parametrize("method,path", ENDPOINTS)
async def test_master_key_cannot_reach_tenant_data(method, path):
    if (method, path) in MASTER_ENDPOINTS:
        pytest.skip("Avsiktligt administrativ endpoint.")
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await _call(client, method, path, {"X-API-Key": MASTER_KEY})
    assert response.status_code == 403, (
        f"{method} {path} svarade {response.status_code} med master-nyckeln — "
        "master saknar tenant och ska nekas mot kunddata."
    )


@pytest.mark.anyio
async def test_public_probes_stay_public():
    """Health-probes måste förbli öppna — Render använder dem för liveness."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            for path in sorted(PUBLIC_PATHS):
                response = await client.get(path)
                assert response.status_code == 200, f"{path} → {response.status_code}"
