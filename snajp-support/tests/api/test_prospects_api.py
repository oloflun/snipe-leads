"""Prospekt-ingången till leads-pipelinen + INV-DATA-002 vid källregistrering."""

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
async def test_create_and_list_prospect():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            created = await client.post(
                "/api/leads/prospects",
                headers=DEMO,
                json={"company_name": "Exempelbolaget AB", "contact_email": "info@exempel.se"},
            )
            assert created.status_code == 201
            prospect = created.json()["prospect"]
            assert prospect["status"] == "new"
            assert prospect["language_state"] == "sv"

            listed = await client.get("/api/leads/prospects", headers=DEMO)
            assert any(p["id"] == prospect["id"] for p in listed.json()["prospects"])


@pytest.mark.anyio
async def test_linkedin_cannot_be_the_first_source_inv_data_002():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            prospect = (
                await client.post(
                    "/api/leads/prospects", headers=DEMO, json={"company_name": "LinkedIn-test AB"}
                )
            ).json()["prospect"]

            refused = await client.post(
                f"/api/leads/prospects/{prospect['id']}/sources",
                headers=DEMO,
                json={
                    "source_url": "https://linkedin.com/in/nagon",
                    "source_type": "linkedin",
                    "lawful_basis": "Berättigat intresse",
                },
            )
            assert refused.status_code == 422
            assert "INV-DATA-002" in refused.json()["detail"]


@pytest.mark.anyio
async def test_linkedin_allowed_as_verification_after_another_source():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            prospect = (
                await client.post(
                    "/api/leads/prospects", headers=DEMO, json={"company_name": "Verifierings-AB"}
                )
            ).json()["prospect"]

            first = await client.post(
                f"/api/leads/prospects/{prospect['id']}/sources",
                headers=DEMO,
                json={
                    "source_url": "https://exempel.se",
                    "source_type": "company_website",
                    "lawful_basis": "Publik företagsinformation",
                },
            )
            assert first.status_code == 201

            second = await client.post(
                f"/api/leads/prospects/{prospect['id']}/sources",
                headers=DEMO,
                json={
                    "source_url": "https://linkedin.com/in/nagon",
                    "source_type": "linkedin",
                    "lawful_basis": "Verifiering av befintlig kontakt",
                },
            )
            assert second.status_code == 201


@pytest.mark.anyio
async def test_sources_for_unknown_prospect_returns_404():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/prospects/00000000-0000-0000-0000-000000000000/sources",
                headers=DEMO,
                json={
                    "source_url": "https://exempel.se",
                    "source_type": "company_website",
                    "lawful_basis": "Publik",
                },
            )
            assert response.status_code == 404


@pytest.mark.anyio
async def test_onboarding_status_endpoint_reports_gaps():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.get("/api/leads/onboarding/status", headers=DEMO)
            assert response.status_code == 200
            body = response.json()
            assert set(body["required"]) == {
                "product_marketing",
                "customer_research",
                "retention_playbook",
            }
            assert body["complete"] is False


@pytest.mark.anyio
async def test_runs_endpoint_is_reachable_for_dashboard():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.get("/api/leads/runs", headers=DEMO)
            assert response.status_code == 200
            assert "runs" in response.json()
