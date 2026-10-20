"""Alla leads går att hämta, sida för sida (Anton 2026-10-21).

GET /api/leads/prospects gav bara de 500 nyaste; main hade 1331 och resten
syntes aldrig i listan. Sidorna räknas på databasraderna, så `fler`/`nasta`
måste föra klienten genom alla, utan att något lead hoppas över eller kommer
två gånger.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_alla_leads_kommer_fram_sida_for_sida():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        skapade = {
            (await storage.create_prospect(DEFAULT_TENANT_ID, company_name=f"Sidbolag {i} AB"))["id"]
            for i in range(650)
        }
        sedda: list[str] = []
        offset, varv = 0, 0
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            while True:
                svar = (await client.get(f"/api/leads/prospects?limit=200&offset={offset}", headers=DEMO)).json()
                sedda += [p["id"] for p in svar["prospects"]]
                varv += 1
                if not svar["fler"]:
                    break
                assert svar["nasta"] > offset
                offset = svar["nasta"]
        assert varv >= 3
        assert skapade <= set(sedda), "varje lead ska komma fram"
        assert len(sedda) == len(set(sedda)), "inget lead två gånger"
