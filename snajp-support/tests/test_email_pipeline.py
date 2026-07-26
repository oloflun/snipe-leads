"""Email-pipelinen: ingest, triage, regler, granskningsflöde och isolation."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}
MASTER = {"X-API-Key": settings.snajp_master_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_mock_seed_triages_and_creates_drafts():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            seeded = await client.post("/api/inbox/mock", headers=DEMO)
            assert seeded.status_code == 201
            assert seeded.json()["ingested"] == 6

            inbox = (await client.get("/api/inbox", headers=DEMO)).json()
            emails = inbox["emails"]
            assert len(emails) == 6

            by_subject = {e["subject"]: e for e in emails}

            login = by_subject["Kan inte logga in på mitt konto"]
            assert login["classification"]["category"] == "teknisk_support"
            assert login["status"] == "awaiting_approval"
            assert login["has_image"] is True

            refund = by_subject["Trasig vara — kräver återbetalning"]
            assert refund["classification"]["escalate"] is True
            assert refund["status"] == "escalated"

            order = by_subject["Har min beställning gått igenom?"]
            assert order["classification"]["category"] == "orderstatus"

            # Alla klassificeringar har konfidens + motivering (beslutslogg).
            assert all(e["classification"]["confidence"] > 0 for e in emails)
            assert all(e["classification"]["reasoning"] for e in emails)


@pytest.mark.anyio
async def test_email_detail_has_attachments_and_decision_log():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            login = next(e for e in emails if "logga in" in e["subject"])

            detail = (await client.get(f"/api/inbox/{login['id']}", headers=DEMO)).json()
            assert detail["attachments"][0]["is_image"] is True
            events = [d["event"] for d in detail["decisions"]]
            assert events[0] == "received"
            assert "classified" in events
            assert "draft_created" in events


@pytest.mark.anyio
async def test_approve_with_edit_sends_and_logs_review():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            pending = next(e for e in emails if e["status"] == "awaiting_approval")
            draft_id = pending["draft"]["id"]

            approved = await client.post(
                f"/api/drafts/{draft_id}/approve",
                headers=DEMO,
                json={"edited_content": "Hej! Redigerat svar från människa."},
            )
            assert approved.status_code == 200
            assert approved.json()["edited"] is True

            detail = (await client.get(f"/api/inbox/{pending['id']}", headers=DEMO)).json()
            assert detail["status"] == "sent"
            assert detail["draft"]["status"] == "approved"
            assert "approved_and_sent" in [d["event"] for d in detail["decisions"]]

            # Dubbelgodkännande blockeras.
            again = await client.post(
                f"/api/drafts/{draft_id}/approve", headers=DEMO, json={}
            )
            assert again.status_code == 409


@pytest.mark.anyio
async def test_auto_rule_sends_without_approval():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            rule = await client.put(
                "/api/rules", headers=DEMO, json={"category": "leverans", "mode": "auto"}
            )
            assert rule.status_code == 200

            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            paket = next(e for e in emails if e["subject"] == "Var är mitt paket?")
            assert paket["status"] == "auto_sent"
            assert paket["draft"]["auto"] is True

            detail = (await client.get(f"/api/inbox/{paket['id']}", headers=DEMO)).json()
            assert "auto_sent" in [d["event"] for d in detail["decisions"]]


@pytest.mark.anyio
async def test_takeover_and_dedupe():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            first = await client.post(
                "/api/inbox/ingest",
                headers=DEMO,
                json={
                    "from": "kund@example.com",
                    "subject": "Var är paketet",
                    "body": "Min leverans är försenad.",
                    "provider_message_id": "ext-123",
                },
            )
            assert first.status_code == 201
            email_id = first.json()["email_id"]

            duplicate = await client.post(
                "/api/inbox/ingest",
                headers=DEMO,
                json={
                    "from": "kund@example.com",
                    "subject": "Var är paketet",
                    "body": "Min leverans är försenad.",
                    "provider_message_id": "ext-123",
                },
            )
            assert duplicate.status_code == 409

            taken = await client.post(f"/api/inbox/{email_id}/takeover", headers=DEMO)
            assert taken.status_code == 200
            detail = (await client.get(f"/api/inbox/{email_id}", headers=DEMO)).json()
            assert detail["status"] == "taken_over"
            assert detail["draft"]["status"] == "rejected"


@pytest.mark.anyio
async def test_inbox_is_tenant_isolated():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            created = await client.post(
                "/api/keys", headers=MASTER, json={"tenant_name": "Annan Butik AB"}
            )
            key_b = {"X-API-Key": created.json()["api_key"]}

            await client.post("/api/inbox/mock", headers=DEMO)
            inbox_a = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            inbox_b = (await client.get("/api/inbox", headers=key_b)).json()["emails"]
            assert len(inbox_a) == 6
            assert inbox_b == []

            # Tenant B kan inte läsa eller ta över A:s mail.
            stolen = await client.get(f"/api/inbox/{inbox_a[0]['id']}", headers=key_b)
            assert stolen.status_code == 404
            takeover = await client.post(
                f"/api/inbox/{inbox_a[0]['id']}/takeover", headers=key_b
            )
            assert takeover.status_code == 404
