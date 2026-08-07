import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_onboarding_chat_endpoint_exists_and_degrades_gracefully_in_simulation():
    """Ingen riktig nyckel i testmiljön -> 503, inte en krasch eller ett
    tyst felaktigt svar."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/onboarding/chat", headers=DEMO, json={"message": "Vi säljer kurser."}
            )
            assert response.status_code == 503
            assert "riktig LLM-nyckel" in response.json()["detail"]


@pytest.mark.anyio
async def test_outreach_draft_endpoint_exists_and_degrades_gracefully_in_simulation():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/outreach/draft",
                headers=DEMO,
                json={
                    "thread_id": "thread-1",
                    "prospect_email": "p@example.se",
                    "company_name": "Exempelbolaget AB",
                    "offer_summary": "60 000 utbildade",
                    "brief": "Skriv ett kallt mejl.",
                },
            )
            assert response.status_code == 503


@pytest.mark.anyio
async def test_research_step_endpoint_exists_and_degrades_gracefully_in_simulation():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/research/step",
                headers=DEMO,
                json={"prospect_id": "prospect-1", "brief": "Researcha bolaget."},
            )
            assert response.status_code == 503


@pytest.mark.anyio
async def test_leads_endpoints_require_a_tenant_key():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/onboarding/chat", json={"message": "hej"}
            )
            assert response.status_code == 401
