"""app/agent/leads_tools.py:s testbara kärnlogik (_impl-funktionerna), inte
via SDK:ns ToolContext-protokoll (omständligt att konstruera i ett test —
se modulens docstring)."""

import pytest

from app.agent.leads_context import OnboardingContext, OutreachContext
from app.agent.leads_tools import (
    _mark_onboarding_done_impl,
    _queue_outreach_draft_impl,
    _request_human_handoff_impl,
    _save_context_doc_impl,
)
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_save_context_doc_persists_and_materializes_product_marketing(tmp_path, monkeypatch):
    monkeypatch.setattr("app.leads.context_pack.VAR_ROOT", tmp_path)
    storage = MemoryStorage()
    ctx = OnboardingContext(storage=storage, tenant_id=TENANT)

    await _save_context_doc_impl(ctx, "product_marketing", "# Exempelbolaget\nSäljer widgets.")

    doc = await storage.get_latest_context_doc(TENANT, kind="product_marketing")
    assert doc["content"] == "# Exempelbolaget\nSäljer widgets."
    assert len(ctx.saved_docs) == 1
    materialized = tmp_path / TENANT / ".agents" / "product-marketing.md"
    assert materialized.read_text(encoding="utf-8") == "# Exempelbolaget\nSäljer widgets."


@pytest.mark.anyio
async def test_save_context_doc_rejects_unknown_kind():
    storage = MemoryStorage()
    ctx = OnboardingContext(storage=storage, tenant_id=TENANT)
    result = await _save_context_doc_impl(ctx, "not_a_real_kind", "x")
    assert "error" in result
    assert ctx.saved_docs == []


@pytest.mark.anyio
async def test_mark_onboarding_done_sets_flag():
    ctx = OnboardingContext(storage=MemoryStorage(), tenant_id=TENANT)
    assert ctx.done is False
    await _mark_onboarding_done_impl(ctx)
    assert ctx.done is True


@pytest.mark.anyio
async def test_queue_outreach_draft_writes_to_storage_never_marks_sent():
    storage = MemoryStorage()
    ctx = OutreachContext(
        storage=storage, tenant_id=TENANT, thread_id="thread-1", prospect_email="p@example.se"
    )

    await _queue_outreach_draft_impl(
        ctx,
        subject="En idé till er",
        body="Hej! **Vi** hjälper er spara tid.",
        language_state="sv",
        humanizer_variant="snajp:humanizer-svenska",
    )

    assert ctx.queued is True
    queued = storage.send_queue[TENANT][0]
    # awaiting_review, inte queued: autonominivån är 'draft' som default
    # (migration 023), och draft betyder att ingenting lämnar huset utan att
    # en människa tryckt skicka. ALDRIG 'sent' — bara schemaläggaren gör det.
    assert queued["status"] == "awaiting_review"
    message = storage.outreach_messages[TENANT][0]
    assert "**" not in message["body"]  # markdown-grinden kördes


@pytest.mark.anyio
async def test_queue_outreach_draft_refuses_on_language_mismatch_and_escalates():
    storage = MemoryStorage()
    ctx = OutreachContext(
        storage=storage, tenant_id=TENANT, thread_id="thread-1", prospect_email="p@example.se"
    )

    await _queue_outreach_draft_impl(
        ctx,
        subject="Subject",
        body="Body",
        language_state="en_confirmed",
        humanizer_variant="snajp:humanizer-svenska",  # fel variant
    )

    assert ctx.queued is False
    assert ctx.escalated is True
    assert storage.send_queue.get(TENANT, []) == []  # inget köades alls


@pytest.mark.anyio
async def test_request_human_handoff_sets_escalation_fields():
    ctx = OutreachContext(
        storage=MemoryStorage(), tenant_id=TENANT, thread_id="thread-1", prospect_email="p@example.se"
    )
    await _request_human_handoff_impl(ctx, "Prospektet svarade positivt")
    assert ctx.escalated is True
    assert ctx.escalation_reason == "Prospektet svarade positivt"
