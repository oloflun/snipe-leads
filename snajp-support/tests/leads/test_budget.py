"""Budgetgrinden (app/leads/budget.py): dygnstaket för leads-tokens.

Grinden är sista försvarslinjen mot både medvetna överkörningar och buggar
som INV-JOB-002 — oavsett hur felet uppstår kan en tenant inte bränna mer än
budgeten per rullande dygn. Se migration 059 för indexet frågan vilar på.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.leads.budget import LeadsBudgetExceededError, kontrollera_leads_budget
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _lagt_tak(monkeypatch):
    monkeypatch.setenv("LEADS_DAILY_TOKEN_BUDGET", "1000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _logga_leads_korning(storage, *, tokens_in: int, tokens_out: int, is_test: bool = False):
    await storage.log_agent_run(
        TENANT,
        agent_type="leads_research",
        pack_version="test",
        skills_used=["snajp:test"],
        input_text="",
        output_text="",
        step_log=[],
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=1,
        is_test=is_test,
    )


async def test_under_taket_slapper_igenom():
    storage = MemoryStorage()
    await _logga_leads_korning(storage, tokens_in=400, tokens_out=100)
    await kontrollera_leads_budget(storage, TENANT)  # ska inte kasta


async def test_over_taket_kastar():
    storage = MemoryStorage()
    await _logga_leads_korning(storage, tokens_in=900, tokens_out=200)
    with pytest.raises(LeadsBudgetExceededError):
        await kontrollera_leads_budget(storage, TENANT)


async def test_testkorningar_raknas_med():
    """is_test-körningar kostar samma pengar hos leverantören och räknas
    därför MOT budgeten — det var en testomkörning som brände de första
    18 kronorna."""
    storage = MemoryStorage()
    await _logga_leads_korning(storage, tokens_in=900, tokens_out=200, is_test=True)
    with pytest.raises(LeadsBudgetExceededError):
        await kontrollera_leads_budget(storage, TENANT)


async def test_supportkorningar_raknas_inte():
    storage = MemoryStorage()
    await storage.log_agent_run(
        TENANT,
        agent_type="support",
        pack_version="test",
        skills_used=["cs:test"],
        input_text="",
        output_text="",
        step_log=[],
        tokens_in=5000,
        tokens_out=5000,
        latency_ms=1,
    )
    await kontrollera_leads_budget(storage, TENANT)  # ska inte kasta


async def test_tak_noll_stanger_grinden(monkeypatch):
    monkeypatch.setenv("LEADS_DAILY_TOKEN_BUDGET", "0")
    get_settings.cache_clear()
    storage = MemoryStorage()
    await _logga_leads_korning(storage, tokens_in=10_000, tokens_out=10_000)
    await kontrollera_leads_budget(storage, TENANT)  # ska inte kasta
