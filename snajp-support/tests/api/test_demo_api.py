import pytest
from httpx import ASGITransport, AsyncClient

from app.config import PUBLIC_DEMO_MAX_PER_SESSION
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_demo_chat_requires_no_api_key():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post("/api/demo/chat", json={"message": "Vad är Snajp?"})
            assert response.status_code == 200
            body = response.json()
            assert body["demo"] is True
            assert body["reply"]


@pytest.mark.anyio
async def test_demo_chat_never_creates_a_ticket_or_customer():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post("/api/demo/chat", json={"message": "Hej!"})
            body = response.json()
            assert "ticket_id" not in body
            assert "customer_id" not in body


@pytest.mark.anyio
async def test_demo_session_cookie_persists_across_requests():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            first = await client.post("/api/demo/chat", json={"message": "Hej"})
            assert "snajp_demo_session" in first.cookies
            second = await client.post("/api/demo/chat", json={"message": "Igen"})
            assert second.cookies.get("snajp_demo_session") == first.cookies.get(
                "snajp_demo_session"
            )


@pytest.mark.anyio
async def test_session_rate_limit_returns_429_once_exceeded():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            last_status = None
            for _ in range(PUBLIC_DEMO_MAX_PER_SESSION + 1):
                resp = await client.post("/api/demo/chat", json={"message": "Hej igen"})
                last_status = resp.status_code
            assert last_status == 429
