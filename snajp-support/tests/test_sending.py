"""Utskicksflödet: godkännande skickar på riktigt, och spärrarna håller."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.email_pipeline import sender
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def sent_box(monkeypatch):
    """Fångar utgående mail i stället för att kontakta en riktig SMTP-server."""
    box: list[dict] = []

    async def fake_send(*, to_email, subject, body, in_reply_to=None):
        box.append(
            {"to": to_email, "subject": subject, "body": body, "in_reply_to": in_reply_to}
        )
        return True, "<test-message-id@snajp>"

    monkeypatch.setattr(sender, "send_reply", fake_send)
    monkeypatch.setattr("app.api.drafts.send_reply", fake_send)
    monkeypatch.setattr(get_settings(), "smtp_host", "smtp.test", raising=False)
    monkeypatch.setattr(get_settings(), "smtp_user", "agent@test.se", raising=False)
    monkeypatch.setattr(get_settings(), "smtp_password", "hemligt-nog-langt", raising=False)
    return box


async def _seed_and_get_pending(client):
    await client.post("/api/inbox/mock", headers=DEMO)
    emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
    return next(e for e in emails if e["status"] == "awaiting_approval")


@pytest.mark.anyio
async def test_approve_sends_real_email_in_thread(sent_box):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            pending = await _seed_and_get_pending(client)

            r = await client.post(
                f"/api/drafts/{pending['draft']['id']}/approve", headers=DEMO, json={}
            )
            assert r.status_code == 200, r.text
            assert r.json()["delivered"] is True
            assert r.json()["status"] == "sent"

            assert len(sent_box) == 1
            assert sent_box[0]["to"] == pending["from_email"]
            # Svaret ska trådas mot kundens ursprungliga mail.
            assert sent_box[0]["in_reply_to"] == pending["provider_message_id"]

            detail = (await client.get(f"/api/inbox/{pending['id']}", headers=DEMO)).json()
            assert detail["status"] == "sent"
            assert "approved_and_sent" in [d["event"] for d in detail["decisions"]]


@pytest.mark.anyio
async def test_send_failure_leaves_draft_pending(monkeypatch):
    """Misslyckad leverans får ALDRIG markera ärendet som besvarat."""
    async def failing_send(*, to_email, subject, body, in_reply_to=None):
        return False, "SMTP-inloggningen nekades — kontrollera app-lösenordet."

    monkeypatch.setattr("app.api.drafts.send_reply", failing_send)
    monkeypatch.setattr(get_settings(), "smtp_host", "smtp.test", raising=False)
    monkeypatch.setattr(get_settings(), "smtp_user", "agent@test.se", raising=False)
    monkeypatch.setattr(get_settings(), "smtp_password", "hemligt-nog-langt", raising=False)

    async with app.router.lifespan_context(app):
        async with _client() as client:
            pending = await _seed_and_get_pending(client)

            r = await client.post(
                f"/api/drafts/{pending['draft']['id']}/approve", headers=DEMO, json={}
            )
            assert r.status_code == 502
            assert "nekades" in r.json()["detail"]

            detail = (await client.get(f"/api/inbox/{pending['id']}", headers=DEMO)).json()
            assert detail["status"] == "awaiting_approval"   # oförändrad
            assert detail["draft"]["status"] == "pending"    # kan försökas igen
            assert "send_failed" in [d["event"] for d in detail["decisions"]]


@pytest.mark.anyio
async def test_approve_without_sending(monkeypatch):
    monkeypatch.setattr(get_settings(), "smtp_host", "", raising=False)
    async with app.router.lifespan_context(app):
        async with _client() as client:
            pending = await _seed_and_get_pending(client)

            r = await client.post(
                f"/api/drafts/{pending['draft']['id']}/approve",
                headers=DEMO,
                json={"send": False},
            )
            assert r.status_code == 200
            assert r.json()["delivered"] is False
            assert r.json()["status"] == "approved"

            detail = (await client.get(f"/api/inbox/{pending['id']}", headers=DEMO)).json()
            assert detail["status"] == "approved"


@pytest.mark.anyio
async def test_approve_without_smtp_configured_is_blocked(monkeypatch):
    """Hellre tydligt fel än att låtsas att kunden fått svar."""
    monkeypatch.setattr(get_settings(), "smtp_host", "", raising=False)
    monkeypatch.setattr(get_settings(), "smtp_user", "", raising=False)
    monkeypatch.setattr(get_settings(), "smtp_password", "", raising=False)
    monkeypatch.setattr(get_settings(), "imap_host", "", raising=False)
    monkeypatch.setattr(get_settings(), "imap_user", "", raising=False)
    monkeypatch.setattr(get_settings(), "imap_password", "", raising=False)

    async with app.router.lifespan_context(app):
        async with _client() as client:
            pending = await _seed_and_get_pending(client)
            r = await client.post(
                f"/api/drafts/{pending['draft']['id']}/approve", headers=DEMO, json={}
            )
            assert r.status_code == 503
            assert "SMTP" in r.json()["detail"]


@pytest.mark.anyio
async def test_auto_rule_is_blocked_by_global_switch(monkeypatch):
    """Även med regeln 'auto' får inget skickas när ALLOW_AUTO_SEND är av."""
    monkeypatch.setattr(get_settings(), "allow_auto_send", False, raising=False)
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.put(
                "/api/rules", headers=DEMO, json={"category": "leverans", "mode": "auto"}
            )
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            paket = next(e for e in emails if e["subject"] == "Var är vår leverans?")

            assert paket["status"] == "awaiting_approval"  # INTE auto_sent
            detail = (await client.get(f"/api/inbox/{paket['id']}", headers=DEMO)).json()
            assert "auto_send_blocked" in [d["event"] for d in detail["decisions"]]


def test_message_id_normalisation():
    assert sender._normalise_message_id("abc@mail.com") == "<abc@mail.com>"
    assert sender._normalise_message_id("<abc@mail.com>") == "<abc@mail.com>"
    assert sender._normalise_message_id("mock-123-1") is None  # inte ett riktigt id
    assert sender._normalise_message_id(None) is None
