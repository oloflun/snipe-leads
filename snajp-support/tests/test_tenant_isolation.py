"""Multi-tenant-isolation: tenant A får aldrig se tenant B:s data."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()
DEMO_KEY = settings.snajp_demo_api_key  # → default-tenanten (Nordlys Handel)
MASTER_KEY = settings.snajp_master_api_key


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _chat_and_wait(client, key: str, message: str, email: str) -> dict:
    headers = {"X-API-Key": key}
    response = await client.post(
        "/api/chat",
        headers=headers,
        json={"message": message, "customer_email": email, "customer_name": "Test"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(50):
        job = (await client.get(f"/api/jobs/{job_id}", headers=headers)).json()
        if job["status"] == "completed":
            return job["result"]
        assert job["status"] != "failed", job
        await asyncio.sleep(0.05)
    raise AssertionError("Jobbet blev aldrig klart.")


async def _create_tenant_b(client) -> dict:
    response = await client.post(
        "/api/keys",
        headers={"X-API-Key": MASTER_KEY},
        json={"tenant_name": "Fjällrävens Sport AB"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_tenant_b_cannot_read_tenant_a_ticket():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_b = await _create_tenant_b(client)

            result_a = await _chat_and_wait(
                client, DEMO_KEY, "Min faktura drogs två gånger.", "kund-a@example.com"
            )
            ticket_id = result_a["ticket_id"]

            # Tenant A ser sitt eget ärende.
            own = await client.get(
                f"/api/tickets/{ticket_id}", headers={"X-API-Key": DEMO_KEY}
            )
            assert own.status_code == 200

            # Tenant B får 404 på samma ärende — inte 403, existensen ska inte läcka.
            other = await client.get(
                f"/api/tickets/{ticket_id}", headers={"X-API-Key": tenant_b["api_key"]}
            )
            assert other.status_code == 404


@pytest.mark.anyio
async def test_tenant_b_cannot_poll_tenant_a_job():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_b = await _create_tenant_b(client)

            response = await client.post(
                "/api/chat",
                headers={"X-API-Key": DEMO_KEY},
                json={"message": "Var är mitt paket?", "customer_email": "kund-a@example.com"},
            )
            job_id = response.json()["job_id"]

            stolen = await client.get(
                f"/api/jobs/{job_id}", headers={"X-API-Key": tenant_b["api_key"]}
            )
            assert stolen.status_code == 404


@pytest.mark.anyio
async def test_kb_is_tenant_specific():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_b = await _create_tenant_b(client)
            key_b = {"X-API-Key": tenant_b["api_key"]}

            # Default-tenanten har den seedade kunskapsbasen; tenant B startar tom.
            kb_a = (await client.get("/api/kb", headers={"X-API-Key": DEMO_KEY})).json()
            kb_b = (await client.get("/api/kb", headers=key_b)).json()
            assert len(kb_a["articles"]) > 0
            assert kb_b["articles"] == []

            # Tom KB ⇒ grundningsregeln tvingar eskalering hos tenant B,
            # medan samma fråga får ett grundat svar hos tenant A.
            fraga = "Vad omfattar garantin och hur lång är garantitiden?"
            result_b = await _chat_and_wait(
                client, tenant_b["api_key"], fraga, "kund-b@example.com"
            )
            assert result_b["escalated"] is True
            assert result_b["kb_sources"] == []

            result_a = await _chat_and_wait(client, DEMO_KEY, fraga, "kund-a@example.com")
            assert result_a["escalated"] is False
            assert len(result_a["kb_sources"]) > 0

            # Tenant B fyller sin egen KB — påverkar inte tenant A:s artikelantal.
            created = await client.post(
                "/api/kb",
                headers=key_b,
                json={
                    "articles": [
                        {
                            "title": "Betalsätt hos Fjällrävens Sport",
                            "content": "Vi accepterar endast Swish och kortbetalning med Visa.",
                            "category": "betalning",
                        }
                    ]
                },
            )
            assert created.status_code == 201
            kb_b_after = (await client.get("/api/kb", headers=key_b)).json()
            kb_a_after = (await client.get("/api/kb", headers={"X-API-Key": DEMO_KEY})).json()
            assert len(kb_b_after["articles"]) == 1
            assert len(kb_a_after["articles"]) == len(kb_a["articles"])


@pytest.mark.anyio
async def test_same_customer_email_is_isolated_per_tenant():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_b = await _create_tenant_b(client)

            result_a = await _chat_and_wait(
                client, DEMO_KEY, "Var är mitt paket?", "samma@example.com"
            )
            result_b = await _chat_and_wait(
                client, tenant_b["api_key"], "Var är mitt paket?", "samma@example.com"
            )
            # Samma e-post ⇒ två olika kundposter, en per tenant.
            assert result_a["customer_id"] != result_b["customer_id"]


@pytest.mark.anyio
async def test_master_key_cannot_touch_customer_data():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/chat",
                headers={"X-API-Key": MASTER_KEY},
                json={"message": "hej", "customer_email": "x@example.com"},
            )
            assert response.status_code == 403
            kb = await client.get("/api/kb", headers={"X-API-Key": MASTER_KEY})
            assert kb.status_code == 403
