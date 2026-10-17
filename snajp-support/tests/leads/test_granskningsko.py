"""Utkastets köstatus (2026-10-07).

En testkörning skickar aldrig till riktiga bolag, och utan schemaläggare
(SEND_QUEUE_POLL_SECONDS osatt) blev ett 'queued' utkast liggande osynligt:
varken skickat eller i granskningskön. Båda går därför till granskning,
oavsett autonominivå. Med schemaläggaren på gäller nivån som förut.
"""

from __future__ import annotations

import json

import pytest

from app.agent.leads_context import OutreachContext
from app.agent.leads_tools import _queue_outreach_draft_impl
from app.config import get_settings
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio
TENANT = "00000000-0000-4000-a000-0000000071c0"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _koa(monkeypatch, *, is_test: bool, schemalaggare: int) -> str:
    monkeypatch.setenv("SEND_QUEUE_POLL_SECONDS", str(schemalaggare))
    get_settings.cache_clear()
    storage = MemoryStorage()
    await storage.set_agent_settings(TENANT, agent_type="leads", settings={"autonomy": "first_contact"})
    prospekt = await storage.create_prospect(TENANT, company_name="Alfa Bygg AB", contact_email="info@alfabygg.se")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
    kontext = OutreachContext(
        storage=storage, tenant_id=TENANT, thread_id=trad["id"], prospect_email="info@alfabygg.se", is_test=is_test
    )
    svar = await _queue_outreach_draft_impl(
        kontext,
        subject="Snabb fråga",
        body="Hej! Vi såg att ni bygger nytt i Mölndal.",
        language_state="sv",
        humanizer_variant="snajp:humanizer-svenska",
    )
    get_settings.cache_clear()
    return json.loads(svar)["status"]


async def test_testkorning_granskas_alltid(monkeypatch):
    assert await _koa(monkeypatch, is_test=True, schemalaggare=60) == "awaiting_review"


async def test_utan_schemalaggare_granskas_utkastet(monkeypatch):
    assert await _koa(monkeypatch, is_test=False, schemalaggare=0) == "awaiting_review"


async def test_med_schemalaggare_galler_autonominivan(monkeypatch):
    assert await _koa(monkeypatch, is_test=False, schemalaggare=60) == "queued"
