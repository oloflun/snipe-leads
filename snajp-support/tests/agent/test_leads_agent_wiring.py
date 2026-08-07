"""Live-entrypoints (leads_agent.py) — samma mockningsprincip som
test_support_agent_wiring.py: mocka bara nätverksgränsen (Runner.run),
bevisa att kontext/instruktioner/verktyg faktiskt kopplas ihop rätt."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agent.leads_agent import (
    build_onboarding_agent,
    build_outreach_agent,
    build_research_agent,
    run_onboarding_turn,
    run_outreach_draft,
    run_research_step,
)
from app.agent.leads_tools import ONBOARDING_TOOLS, OUTREACH_TOOLS
from app.agent.research_tools import RESEARCH_TOOLS
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_deepseek_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_build_onboarding_agent_uses_onboarding_tools_only():
    agent, skills_used = build_onboarding_agent(existing_product_marketing=None)
    assert agent.tools == ONBOARDING_TOOLS
    assert skills_used == ["mk:product-marketing", "mk:customer-research", "mk:churn-prevention"]


def test_build_outreach_agent_uses_outreach_tools_only():
    agent, skills_used = build_outreach_agent(
        tenant_name="Livrustning", company_name="Exempelbolaget", offer_summary="X", context_pack=""
    )
    assert agent.tools == OUTREACH_TOOLS
    assert "sa:draft-outreach" in skills_used


def test_build_research_agent_uses_research_tools_only():
    agent, skills_used = build_research_agent(tenant_name="Livrustning", context_pack="")
    assert agent.tools == RESEARCH_TOOLS
    assert skills_used[0] == "mk:customer-research"
    assert "mk:sales-enablement" in skills_used


class _FakeResult:
    def __init__(self, final_output=""):
        self.final_output = final_output


@pytest.mark.anyio
async def test_run_onboarding_turn_reads_existing_doc_and_returns_progress():
    storage = MemoryStorage()
    await storage.save_context_doc(TENANT, kind="product_marketing", content="Redan insamlat")

    async def fake_runner_run(agent, agent_input, context, max_turns):
        # Simulerar att agenten anropade save_context_doc under körningen.
        context.saved_docs.append({"kind": "customer_research", "version": 1})
        return _FakeResult("Tack, jag har antecknat det.")

    with patch("app.agent.leads_agent.Runner.run", new=AsyncMock(side_effect=fake_runner_run)):
        result = await run_onboarding_turn(storage, TENANT, message="Vi säljer utbildningar.")

    assert result["reply"] == "Tack, jag har antecknat det."
    assert result["saved_docs"] == ["customer_research"]
    assert result["skills_used"] == [
        "mk:product-marketing",
        "mk:customer-research",
        "mk:churn-prevention",
    ]


@pytest.mark.anyio
async def test_run_research_step_returns_scraped_sources_recorded_on_context():
    storage = MemoryStorage()

    async def fake_runner_run(agent, agent_input, context, max_turns):
        context.scraped_sources.append({"url": "https://exempelbolaget.se", "length": 500})
        return _FakeResult("Research klar.")

    with patch("app.agent.leads_agent.Runner.run", new=AsyncMock(side_effect=fake_runner_run)):
        result = await run_research_step(
            storage,
            TENANT,
            prospect_id="prospect-1",
            tenant_name="Livrustning",
            context_pack="### Kontextpaket\n...",
            brief="Researcha exempelbolaget.se.",
        )

    assert result["scraped_sources"] == [{"url": "https://exempelbolaget.se", "length": 500}]
    assert "mk:customer-research" in result["skills_used"]


@pytest.mark.anyio
async def test_run_outreach_draft_reflects_queued_state_from_context():
    storage = MemoryStorage()

    async def fake_runner_run(agent, agent_input, context, max_turns):
        context.queued = True
        return _FakeResult("Utkast köat.")

    with patch("app.agent.leads_agent.Runner.run", new=AsyncMock(side_effect=fake_runner_run)):
        result = await run_outreach_draft(
            storage,
            TENANT,
            thread_id="thread-1",
            prospect_email="p@example.se",
            tenant_name="Livrustning",
            company_name="Exempelbolaget",
            offer_summary="60 000 utbildade, 780 omdömen",
            context_pack="### Kontextpaket\n...",
            brief="Skriv ett kallt mejl om vår utbildning.",
        )

    assert result["queued"] is True
    assert result["escalated"] is False
    assert "sa:draft-outreach" in result["skills_used"]


@pytest.mark.anyio
async def test_run_outreach_draft_reflects_escalation_from_context():
    storage = MemoryStorage()

    async def fake_runner_run(agent, agent_input, context, max_turns):
        context.escalated = True
        context.escalation_reason = "Prospektet ställde en prisfråga agenten inte får svara på."
        return _FakeResult("Eskalerat.")

    with patch("app.agent.leads_agent.Runner.run", new=AsyncMock(side_effect=fake_runner_run)):
        result = await run_outreach_draft(
            storage,
            TENANT,
            thread_id="thread-1",
            prospect_email="p@example.se",
            tenant_name="Livrustning",
            company_name="Exempelbolaget",
            offer_summary="X",
            context_pack="",
            brief="Svara på prospektets fråga.",
        )

    assert result["queued"] is False
    assert result["escalated"] is True
    assert "prisfråga" in result["escalation_reason"]
