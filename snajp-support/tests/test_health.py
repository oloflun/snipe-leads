"""Health-endpoints: driftläget ska gå att läsa av utan att gissa."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_liveness_is_cheap_and_always_ok():
    """Renders health check får inte falla bara för att en nyckel saknas."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            r = await client.get("/health/live")
            assert r.status_code == 200
            assert r.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_readiness_reports_degraded_without_crashing():
    """Utan nycklar körs tjänsten degraderat — men den är fortfarande användbar,
    så readiness ska ge 200 med varningar, inte 503."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            r = await client.get("/health/ready")
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "ok"
            assert body["degraded"] is True
            assert any("LLM" in w for w in body["warnings"])
            assert any("DATABASE_URL" in w for w in body["warnings"])


@pytest.mark.anyio
async def test_api_health_requires_key_and_is_tenant_aware():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            assert (await client.get("/api/health")).status_code == 401

            r = await client.get("/api/health", headers=DEMO)
            assert r.status_code == 200
            body = r.json()
            assert body["tenant_name"]
            # Demon har aldrig en riktig inkorg kopplad.
            assert body["has_inbox"] is False
            assert body["auto_send_enabled"] is False
