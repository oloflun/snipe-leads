"""GET /api/usage — journalens tenant-scopade förbrukning (Livrustning-piloten)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

pytestmark = pytest.mark.anyio

DEMO_KEY = get_settings().snajp_demo_api_key


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _logga_korning(storage, tenant_id: str, *, tokens_in: int, tokens_out: int, is_test=False):
    await storage.log_agent_run(
        tenant_id,
        agent_type="support",
        pack_version="test",
        skills_used=[],
        input_text="fråga",
        output_text="svar",
        step_log=[],
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=1,
        is_test=is_test,
    )


async def test_usage_summerar_per_dag(monkeypatch):
    monkeypatch.setenv("SUPPORT_BUDGET_NORDLYS_HANDEL", "1000000")
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _logga_korning(storage, DEFAULT_TENANT_ID, tokens_in=100, tokens_out=50)
        await _logga_korning(storage, DEFAULT_TENANT_ID, tokens_in=30, tokens_out=20, is_test=True)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.get("/api/usage", headers={"X-API-Key": DEMO_KEY})
            assert svar.status_code == 200
            data = svar.json()

        [dag] = data["dagar"]
        assert dag["korningar"] == 1
        assert dag["korningar_test"] == 1
        assert dag["tokens_in"] == 130
        assert dag["tokens_out"] == 70
        assert data["budget"]["tak"] == 1000000
        assert data["budget"]["forbrukat_24h"] == 200


async def test_usage_kraver_tenantnyckel():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            utan = await client.get("/api/usage")
            assert utan.status_code == 401
            master = await client.get(
                "/api/usage", headers={"X-API-Key": get_settings().snajp_master_api_key}
            )
            assert master.status_code == 403
