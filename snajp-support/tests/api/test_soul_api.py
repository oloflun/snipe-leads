"""SOUL-endpointsen — kundens enda väg att skriva sitt röstdokument.

Kör mot den riktiga ASGI-appen, inte mot funktionerna direkt: taket och
tenant-scopingen sitter delvis i pydantic-modellen och i require_tenant, och
ett test som anropar route-funktionen direkt hoppar över båda.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.leads.soul import SOUL_MAX_CHARS
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_soul_round_trips():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            empty = await client.get("/api/leads/soul", headers=DEMO)
            assert empty.status_code == 200
            assert empty.json()["content"] == ""
            assert empty.json()["max_chars"] == SOUL_MAX_CHARS

            saved = await client.put(
                "/api/leads/soul",
                headers=DEMO,
                json={"content": "Vi säger du, aldrig ni. Korta meningar."},
            )
            assert saved.status_code == 200
            assert saved.json()["saved"] is True

            again = await client.get("/api/leads/soul", headers=DEMO)
            assert "Vi säger du" in again.json()["content"]


@pytest.mark.anyio
async def test_soul_over_the_cap_is_refused_at_the_api_boundary():
    """422 från pydantic, inte ett 500 längre in. Taket finns dessutom en
    gång till i render_soul — se test_inv_sec_009."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.put(
                "/api/leads/soul", headers=DEMO, json={"content": "x" * (SOUL_MAX_CHARS + 1)}
            )
            assert response.status_code == 422


@pytest.mark.anyio
async def test_soul_requires_a_tenant_key():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            assert (await client.get("/api/leads/soul")).status_code in (401, 403, 422)
