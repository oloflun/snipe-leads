"""GET /api/leads/korningar — körningslistan ur liggaren (migration 080).

Routen läser bara; det som prövas är tenantgränsen, 404 för okänd rad, och
att tillstånd och felorsak når klienten oförvanskade.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
ANNAN_TENANT = "00000000-0000-0000-0000-00000000d4d4"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_korningslistan_och_en_korning():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await storage.set_leads_job_status(
            DEFAULT_TENANT_ID, job_id="k-1", status="processing", scope="batch",
            korning={"mal": 3, "levererade": 1, "undersokta": 2, "pagaende": 1, "klar": False, "tratt": [], "jobs": []},
            is_test=True,
        )
        await storage.set_leads_job_status(
            DEFAULT_TENANT_ID, job_id="k-2", status="failed", scope="lista", error="Budgeten är slut."
        )
        # En annan tenants körning får aldrig synas (RLS i Postgres, filtret i minnet).
        await storage.set_leads_job_status(ANNAN_TENANT, job_id="k-9", status="completed", scope="batch")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.get("/api/leads/korningar", headers=DEMO)
            assert svar.status_code == 200
            ids = [r["job_id"] for r in svar.json()["korningar"]]
            assert "k-1" in ids and "k-2" in ids and "k-9" not in ids

            en = await client.get("/api/leads/korningar/k-1", headers=DEMO)
            assert en.status_code == 200
            assert en.json()["korning"]["levererade"] == 1
            assert en.json()["is_test"] is True
            assert en.json()["status"] == "processing"

            fel = await client.get("/api/leads/korningar/k-2", headers=DEMO)
            assert fel.json()["error"] == "Budgeten är slut." and fel.json()["korning"] is None

            assert (await client.get("/api/leads/korningar/k-9", headers=DEMO)).status_code == 404
            assert (await client.get("/api/leads/korningar/finns-inte", headers=DEMO)).status_code == 404
            assert (await client.get("/api/leads/korningar")).status_code in (401, 403)
