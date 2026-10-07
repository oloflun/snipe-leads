"""Svaren ska nå Leads › Inkorg, och det som skickats ska synas i Skickat
(Sebbe 2026-10-07).

Utskicken gick från plattformens adress utan Reply-To, så prospektets svar
hamnade aldrig i kundens synkade brevlåda — den Leads › Inkorg läser. Nu bär
utskicket kundens brevlåda (leads-brevlådan först) som Reply-To, bolaget blir
Kontaktat när mejlet gått ut, och GET /api/leads/skickat listar mejlen."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads.scheduler import skicka_godkant
from app.main import app
from app.storage.memory import MemoryStorage
from tests.leads.test_scheduler import TENANT, WITHIN_WINDOW_UTC, _seed

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _ResendLik:
    """Tar emot avsändarparametrarna, som ResendMailer."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, *, to, subject, body, html=None, from_email=None, from_name=None, reply_to=None, **_):
        self.sent.append({"to": to, "reply_to": reply_to, "from_email": from_email})


async def _godkant_utkast(storage: MemoryStorage) -> tuple[str, str]:
    item_id, thread_id, _ = _seed(storage, autonomy="draft", scheduled_at=WITHIN_WINDOW_UTC)
    storage.outreach_messages[TENANT] = [m for m in storage.outreach_messages[TENANT] if m["thread_id"] != "historik"]
    storage.send_queue[TENANT][-1]["status"] = "awaiting_review"
    prospekt = await storage.create_prospect(TENANT, company_name="Svarsbolaget AB", contact_email="prospect@example.se")
    storage.outreach_threads[TENANT][thread_id]["prospect_id"] = prospekt["id"]
    return item_id, prospekt["id"]


async def test_reply_to_ar_leadsbrevladan_och_bolaget_blir_kontaktat():
    storage, provider = MemoryStorage(), _ResendLik()
    await storage.upsert_mailbox(TENANT, provider="imap", address="support@kund.se", syfte="support")
    await storage.upsert_mailbox(TENANT, provider="imap", address="leads@kund.se", syfte="leads")
    item_id, prospect_id = await _godkant_utkast(storage)

    utfall, _ = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    assert utfall == "sent"
    assert provider.sent[0]["reply_to"] == "leads@kund.se"
    assert (await storage.get_prospect(TENANT, prospect_id))["status"] == "contacted"


async def test_utan_brevlada_ingen_reply_to():
    storage, provider = MemoryStorage(), _ResendLik()
    item_id, _ = await _godkant_utkast(storage)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)
    assert provider.sent[0]["reply_to"] is None


async def test_svarat_bolag_flyttas_inte_tillbaka_till_kontaktad():
    storage, provider = MemoryStorage(), _ResendLik()
    item_id, prospect_id = await _godkant_utkast(storage)
    await storage.update_prospect(TENANT, prospect_id, status="replied")
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)
    assert (await storage.get_prospect(TENANT, prospect_id))["status"] == "replied"


async def test_skickat_listar_skickade_mejl_med_bolag():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        prospekt = await storage.create_prospect(
            DEFAULT_TENANT_ID, company_name="Skickatbolaget AB", contact_email="info@skickat.se"
        )
        trad = await storage.ensure_outreach_thread(DEFAULT_TENANT_ID, prospect_id=prospekt["id"])
        koat = await storage.queue_outreach_message(
            DEFAULT_TENANT_ID, thread_id=trad["id"], subject="Nya kontoret", body="Hej!\n\nText.",
            humanizer_variant="x", scheduled_at=WITHIN_WINDOW_UTC, status="awaiting_review",
        )
        # Ett utkast som inte skickats än ska inte synas.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            fore = (await client.get("/api/leads/skickat", headers=DEMO)).json()["skickat"]
            assert all(r["company_name"] != "Skickatbolaget AB" for r in fore)

            await storage.mark_outreach_message_sent(DEFAULT_TENANT_ID, koat["message"]["id"], WITHIN_WINDOW_UTC)
            rader = (await client.get("/api/leads/skickat", headers=DEMO)).json()["skickat"]
            rad = next(r for r in rader if r["company_name"] == "Skickatbolaget AB")
            assert rad["subject"] == "Nya kontoret" and rad["body"].startswith("Hej!")
            assert rad["prospect_email"] == "info@skickat.se" and rad["prospect_id"] == prospekt["id"]
            assert rad["svarat"] is False
