"""Pilot-arbetsytan är skild från den publika demon.

Kärnkravet: den publika demon får ALDRIG kunna dra in eller läsa riktiga
kundmail, ens om någon anropar API:t direkt med demo-nyckeln.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, PILOT_TENANT_ID, get_settings
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}
PILOT_KEY = "snajp_pilot_test_key_0123456789"
PILOT = {"X-API-Key": PILOT_KEY}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def pilot_enabled(monkeypatch):
    monkeypatch.setattr(get_settings(), "snajp_pilot_api_key", PILOT_KEY, raising=False)
    monkeypatch.setattr(get_settings(), "imap_tenant", "pilot", raising=False)
    monkeypatch.setattr(get_settings(), "imap_host", "imap.gmail.com", raising=False)
    monkeypatch.setattr(get_settings(), "imap_user", "pilot@example.com", raising=False)
    monkeypatch.setattr(get_settings(), "imap_password", "app-losenord-langt-nog", raising=False)


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_demo_cannot_sync_real_inbox(pilot_enabled):
    """Demo-nyckeln får inte hämta riktiga mail — även om IMAP är konfigurerat."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            r = await client.post("/api/inbox/sync", headers=DEMO)
            assert r.status_code == 200
            body = r.json()
            assert body["fetched"] == 0
            assert "ingen kopplad inkorg" in body["error"]


@pytest.mark.anyio
async def test_pilot_and_demo_have_separate_inboxes(pilot_enabled):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            # Demon seedar testmail i sin egen arbetsyta.
            await client.post("/api/inbox/mock", headers=DEMO)
            demo_inbox = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            pilot_inbox = (await client.get("/api/inbox", headers=PILOT)).json()["emails"]

            assert len(demo_inbox) == 6
            assert pilot_inbox == []  # pilotens arbetsyta är orörd

            # Och tvärtom: pilotens ärenden syns inte i demon.
            await client.post(
                "/api/inbox/ingest",
                headers=PILOT,
                json={
                    "from": "riktig.kund@example.com",
                    "subject": "Fråga om hjärtstartare",
                    "body": "Hur ofta behöver elektroderna bytas?",
                },
            )
            pilot_after = (await client.get("/api/inbox", headers=PILOT)).json()["emails"]
            demo_after = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            assert len(pilot_after) == 1
            assert len(demo_after) == 6
            assert all("hjärtstartare" not in e["subject"] for e in demo_after)


@pytest.mark.anyio
async def test_health_reports_inbox_per_workspace(pilot_enabled):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            demo_health = (await client.get("/api/health", headers=DEMO)).json()
            pilot_health = (await client.get("/api/health", headers=PILOT)).json()
            assert demo_health["has_inbox"] is False
            assert pilot_health["has_inbox"] is True


@pytest.mark.anyio
async def test_pilot_key_disabled_by_default():
    """Utan SNAJP_PILOT_API_KEY finns ingen pilot-arbetsyta att nå."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            r = await client.get("/api/inbox", headers=PILOT)
            assert r.status_code == 401


def test_tenant_ids_are_distinct():
    assert PILOT_TENANT_ID != DEFAULT_TENANT_ID
