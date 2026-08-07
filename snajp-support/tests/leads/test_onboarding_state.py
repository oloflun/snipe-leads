"""Efterhandstrigger av onboarding: pipelinen får ALDRIG dödlåsa sig på
utebliven onboarding, men den får heller aldrig tyst låtsas att underlaget
finns."""

import pytest

from app.leads.context_pack import build_context_pack
from app.leads.onboarding_state import get_onboarding_state, render_gap_notice
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_fresh_tenant_reports_everything_missing():
    state = await get_onboarding_state(MemoryStorage(), TENANT)
    assert state.complete is False
    assert state.started is False
    assert set(state.missing) == {"product_marketing", "customer_research", "retention_playbook"}


@pytest.mark.anyio
async def test_partial_onboarding_reports_exactly_what_is_missing():
    storage = MemoryStorage()
    await storage.save_context_doc(TENANT, kind="product_marketing", content="Vi säljer X.")
    state = await get_onboarding_state(storage, TENANT)
    assert state.started is True
    assert state.complete is False
    assert state.present == ("product_marketing",)
    assert set(state.missing) == {"customer_research", "retention_playbook"}


@pytest.mark.anyio
async def test_complete_onboarding_reports_complete():
    storage = MemoryStorage()
    for kind in ("product_marketing", "customer_research", "retention_playbook"):
        await storage.save_context_doc(TENANT, kind=kind, content="innehåll")
    state = await get_onboarding_state(storage, TENANT)
    assert state.complete is True
    assert state.missing == ()


@pytest.mark.anyio
async def test_whitespace_only_document_counts_as_missing():
    storage = MemoryStorage()
    await storage.save_context_doc(TENANT, kind="product_marketing", content="   ")
    state = await get_onboarding_state(storage, TENANT)
    assert "product_marketing" in state.missing


@pytest.mark.anyio
async def test_context_pack_is_usable_even_with_zero_onboarding():
    """Kärnkravet: Fas B/C ska kunna köra ändå — men med explicita luckor."""
    pack, missing = await build_context_pack(MemoryStorage(), TENANT)
    assert pack.strip()
    assert "OFULLSTÄNDIG ONBOARDING" in pack
    assert len(missing) == 3


@pytest.mark.anyio
async def test_gap_notice_forbids_offers_when_retention_playbook_missing():
    """INV-AGENT-001 måste hålla även när playbooken aldrig skapats."""
    storage = MemoryStorage()
    await storage.save_context_doc(TENANT, kind="product_marketing", content="X")
    await storage.save_context_doc(TENANT, kind="customer_research", content="Y")
    pack, missing = await build_context_pack(storage, TENANT)
    assert missing == ("retention_playbook",)
    assert "Erbjud därför ingenting" in pack


@pytest.mark.anyio
async def test_no_gap_notice_when_onboarding_is_complete():
    storage = MemoryStorage()
    for kind in ("product_marketing", "customer_research", "retention_playbook"):
        await storage.save_context_doc(TENANT, kind=kind, content="innehåll " + kind)
    pack, missing = await build_context_pack(storage, TENANT)
    assert missing == ()
    assert "OFULLSTÄNDIG ONBOARDING" not in pack
    assert "innehåll retention_playbook" in pack


def test_render_gap_notice_is_empty_for_complete_state():
    from app.leads.onboarding_state import OnboardingState

    assert render_gap_notice(OnboardingState(present=("a",), missing=())) == ""
