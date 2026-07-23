import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

DEMO_KEY = get_settings().snajp_demo_api_key


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_health_and_auth():
    async with app.router.lifespan_context(app):
        async with await _client() as client:
            health = await client.get("/health")
            assert health.status_code == 200
            assert health.json()["mode"] in ("simulation", "live")

            denied = await client.post("/api/chat", json={"message": "hej"})
            assert denied.status_code == 401


@pytest.mark.anyio
async def test_chat_job_flow_simulation():
    async with app.router.lifespan_context(app):
        async with await _client() as client:
            headers = {"X-API-Key": DEMO_KEY}
            response = await client.post(
                "/api/chat",
                headers=headers,
                json={
                    "message": "Min faktura drogs två gånger, vad gör jag?",
                    "subject": "Dubbeldragning",
                    "customer_email": "test@example.com",
                    "customer_name": "Test Person",
                },
            )
            assert response.status_code == 202
            job_id = response.json()["job_id"]

            result = None
            for _ in range(50):
                job = (await client.get(f"/api/jobs/{job_id}", headers=headers)).json()
                if job["status"] == "completed":
                    result = job["result"]
                    break
                assert job["status"] != "failed", job
                await asyncio.sleep(0.05)

            assert result is not None
            assert result["category"] == "betalning"
            assert result["reply"]
            assert result["ticket_id"]


@pytest.mark.anyio
async def test_triage_batch():
    async with app.router.lifespan_context(app):
        async with await _client() as client:
            response = await client.post(
                "/api/triage",
                headers={"X-API-Key": DEMO_KEY},
                json={
                    "emails": [
                        {"from": "a@ex.se", "subject": "Paket försenat", "body": "Var är min leverans?"},
                        {"from": "b@ex.se", "subject": "Arg", "body": "Jag vill ha pengarna tillbaka NU!!"},
                    ]
                },
            )
            assert response.status_code == 200
            results = response.json()["results"]
            assert results[0]["category"] == "leverans"
            assert results[1]["escalate"] is True
            assert all(r["draft_reply"] for r in results)
