"""Förbrukningsmätning per tenant — underlag för framtida tak och fakturering.

Testerna kör i simuleringsläge, så tokens är noll. Det som bevisas är att varje
svar bokförs, att det bokförs på RÄTT tenant, och att en tenant aldrig ser en
annans förbrukning.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()
DEMO_KEY = settings.snajp_demo_api_key
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


async def _onboard(client, name: str) -> dict:
    response = await client.post(
        "/api/keys", headers={"X-API-Key": MASTER_KEY}, json={"tenant_name": name}
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_every_reply_is_metered():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            before = (await client.get("/api/usage", headers={"X-API-Key": DEMO_KEY})).json()

            await _chat_and_wait(client, DEMO_KEY, "Var är mitt paket?", "a@example.com")
            await _chat_and_wait(client, DEMO_KEY, "Hur lång är garantin?", "b@example.com")

            after = (await client.get("/api/usage", headers={"X-API-Key": DEMO_KEY})).json()
            assert after["responses"] == before["responses"] + 2
            # Simuleringsläget kostar inget men ska ändå synas som aktivitet.
            assert after["simulated_responses"] == before["simulated_responses"] + 2
            assert {k["kind"] for k in after["per_kind"]} >= {"chat"}


@pytest.mark.anyio
async def test_usage_is_isolated_per_tenant():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_b = await _onboard(client, "Granhult Trä")
            key_b = tenant_b["api_key"]

            demo_before = (
                await client.get("/api/usage", headers={"X-API-Key": DEMO_KEY})
            ).json()["responses"]

            # Tre svar hos tenant B.
            for i in range(3):
                await _chat_and_wait(client, key_b, "Var är mitt paket?", f"b{i}@example.com")

            usage_b = (await client.get("/api/usage", headers={"X-API-Key": key_b})).json()
            usage_demo = (
                await client.get("/api/usage", headers={"X-API-Key": DEMO_KEY})
            ).json()

            assert usage_b["responses"] == 3
            # Demo-tenantens siffra rörs inte av tenant B:s trafik.
            assert usage_demo["responses"] == demo_before
            assert usage_b["tenant_name"] == "Granhult Trä"


@pytest.mark.anyio
async def test_triage_batch_counts_every_email():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Vikbo Bygg")
            key = {"X-API-Key": tenant["api_key"]}

            response = await client.post(
                "/api/triage",
                headers=key,
                json={
                    "emails": [
                        {"from": "k1@example.com", "subject": "Frakt", "body": "Var är paketet?"},
                        {"from": "k2@example.com", "subject": "Faktura", "body": "Fel belopp."},
                    ]
                },
            )
            assert response.status_code == 200

            usage = (await client.get("/api/usage", headers=key)).json()
            triage = next(k for k in usage["per_kind"] if k["kind"] == "triage")
            # Två mail = två svar, även om det loggas som en batch-rad.
            assert triage["responses"] == 2


@pytest.mark.anyio
async def test_usage_window_respects_days_parameter():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Ekbacken Ost")
            key = {"X-API-Key": tenant["api_key"]}

            await _chat_and_wait(client, tenant["api_key"], "Hej!", "kund@example.com")

            # Färsk aktivitet syns i fönstret ...
            assert (await client.get("/api/usage?days=1", headers=key)).json()["responses"] == 1
            # ... och ogiltiga fönster avvisas i stället för att tyst tolkas om.
            assert (await client.get("/api/usage?days=0", headers=key)).status_code == 422
            assert (await client.get("/api/usage?days=999", headers=key)).status_code == 422
