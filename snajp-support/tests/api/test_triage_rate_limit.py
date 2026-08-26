"""Triage-endpointen står bakom samma timtak som chatten (migration 019).

Routen var den enda LLM-vägen utan enforce(): anonymt nåbar genom
Next-proxyn, upp till 20 mejl per anrop, ett LLM-anrop per mejl i skarpt
läge. Utan taket var den den billigaste vägen att bränna nyckeln — och att
tömma tenantkvoten för de riktiga kunder som delar den.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import rate_limit_db
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO_KEY = get_settings().snajp_demo_api_key

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _mejl(n: int = 1) -> dict:
    return {
        "emails": [
            {
                "sender": f"kund{i}@example.com",
                "subject": "Var är mitt paket?",
                "body": "Beställde för en vecka sedan och inget har kommit.",
            }
            for i in range(n)
        ]
    }


async def test_triage_far_429_nar_tenanttaket_ar_natt():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        scopes = rate_limit_db.scopes_for(DEFAULT_TENANT_ID, None)
        await rate_limit_db.record(storage, scopes, rate_limit_db.TENANT_HOURLY_LLM_CALLS)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/triage", headers={"X-API-Key": DEMO_KEY}, json=_mejl()
            )
        assert response.status_code == 429
        # detail, inte error: FastAPI:s HTTPException-form, samma som chatten —
        # och frontenden läser numera båda fälten (SupportChat.tsx).
        assert "tak" in response.json()["detail"].lower()


async def test_triage_under_taket_fungerar_som_forut():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/triage", headers={"X-API-Key": DEMO_KEY}, json=_mejl(2)
            )
        assert response.status_code == 200
        assert len(response.json()["results"]) == 2
