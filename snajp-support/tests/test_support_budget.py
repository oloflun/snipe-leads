"""Supportbudgeten (app/budget.py): dygnstak per tenant, förvarning vid 80 %,
larm och 429 vid taket — och avstängd som default.

Mot MemoryStorage: sum_support_tokens finns i båda lagren (samma mönster som
sum_leads_tokens, se test_rate_limit_db för resonemanget).
"""

from __future__ import annotations

import pytest

from app import budget
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture(autouse=True)
def _rent_larmminne():
    budget.nollstall_larmminne()
    yield
    budget.nollstall_larmminne()


async def _tenant_med_forbrukning(storage, *, tokens: int) -> str:
    tenant = await storage.create_tenant(slug="livrustning", name="Livrustning AB")
    if tokens:
        await storage.log_agent_run(
            tenant["id"],
            agent_type="support",
            pack_version="test",
            skills_used=[],
            input_text="fråga",
            output_text="svar",
            step_log=[],
            tokens_in=tokens // 2,
            tokens_out=tokens - tokens // 2,
            latency_ms=1,
        )
    return tenant["id"]


async def test_avstangd_som_default(storage):
    """Utan env-tak är grinden av — befintliga kunder får inget nytt tak av
    en deploy."""
    tenant_id = await _tenant_med_forbrukning(storage, tokens=10_000_000)
    await budget.kontrollera_support_budget(storage, tenant_id)  # ska inte kasta


async def test_under_taket_slapper_igenom(storage, monkeypatch):
    monkeypatch.setenv("SUPPORT_BUDGET_LIVRUSTNING", "1000")
    tenant_id = await _tenant_med_forbrukning(storage, tokens=500)
    await budget.kontrollera_support_budget(storage, tenant_id)
    assert await storage.list_platform_events(tenant_id=tenant_id) == []


async def test_forvarning_vid_80_procent(storage, monkeypatch):
    monkeypatch.setenv("SUPPORT_BUDGET_LIVRUSTNING", "1000")
    tenant_id = await _tenant_med_forbrukning(storage, tokens=850)

    await budget.kontrollera_support_budget(storage, tenant_id)  # kastar inte

    handelser = await storage.list_platform_events(tenant_id=tenant_id)
    assert len(handelser) == 1
    assert handelser[0]["level"] == "warning"
    assert handelser[0]["source"] == "budget"
    assert "85 %" in handelser[0]["message"]


async def test_forvarningen_dedupliceras_per_dygn(storage, monkeypatch):
    monkeypatch.setenv("SUPPORT_BUDGET_LIVRUSTNING", "1000")
    tenant_id = await _tenant_med_forbrukning(storage, tokens=850)

    await budget.kontrollera_support_budget(storage, tenant_id)
    await budget.kontrollera_support_budget(storage, tenant_id)

    handelser = await storage.list_platform_events(tenant_id=tenant_id)
    assert len(handelser) == 1


async def test_taket_stoppar_och_larmar(storage, monkeypatch):
    monkeypatch.setenv("SUPPORT_BUDGET_LIVRUSTNING", "1000")
    tenant_id = await _tenant_med_forbrukning(storage, tokens=1200)

    with pytest.raises(budget.SupportBudgetExceededError) as caught:
        await budget.kontrollera_support_budget(storage, tenant_id)
    assert str(caught.value) == budget.KUNDTEXT_BUDGET

    handelser = await storage.list_platform_events(tenant_id=tenant_id)
    assert [h["level"] for h in handelser] == ["error"]


async def test_per_tenant_env_vinner_over_global(storage, monkeypatch):
    """SUPPORT_BUDGET_<SLUG> är pilotens ratt: den ska gälla före det
    globala taket, åt båda hållen."""
    monkeypatch.setenv("SUPPORT_DAILY_TOKEN_BUDGET", "100")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("SUPPORT_BUDGET_LIVRUSTNING", "1000000")
    tenant_id = await _tenant_med_forbrukning(storage, tokens=500)
    try:
        await budget.kontrollera_support_budget(storage, tenant_id)  # 500 < 1M
    finally:
        get_settings.cache_clear()


async def test_trasigt_envvarde_faller_tillbaka(storage, monkeypatch):
    monkeypatch.setenv("SUPPORT_BUDGET_LIVRUSTNING", "hundra")
    assert budget.budget_for("livrustning") == 0  # globala defaulten (av)


async def test_lagringsfel_slapper_igenom():
    """Fail-open: en trasig mätning får inte stoppa en betalande kunds chatt."""

    class TrasigStorage:
        async def get_tenant(self, tenant_id):
            raise RuntimeError("databasen är nere")

    await budget.kontrollera_support_budget(TrasigStorage(), "vilken-som-helst")
