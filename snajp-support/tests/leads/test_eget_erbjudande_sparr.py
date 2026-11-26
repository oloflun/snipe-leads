"""Inget utkast utan kundens egen produkt (kunddemon 2026-11-24).

Onboardingen skrev aldrig `settings.produkter`. Med tom produktlista valdes
varken produkt eller erbjudande, ingen spärr stoppade utkastet, och modellen
lånade Snajps Supportagent ur skrivstilens exempel. Spärren går före modellen:
körningen stannar vid starten, innan research kostar något, med ett besked som
säger vad kunden ska göra.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import leads as leads_api
from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads.business_context import SAKNAR_PRODUKT, MissingBusinessContextError, require_egen_produkt
from app.main import app
from app.storage.memory import MemoryStorage

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
FEJKAD = "sk-" + "a" * 37


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def live_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("DEEPSEEK_API_KEY", FEJKAD)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


#: Där produkterna faktiskt ställs in: Inställningar › Iris › Målgrupp och
#: automation (components/leads/IrisInstallningar.tsx renderar IrisProdukter).
PLATS = "Inställningar › Målgrupp och automation"


@pytest.mark.anyio
async def test_tom_produktlista_ger_en_kod_och_svensk_text():
    """Beskedet bar förut svenska och engelska i samma sträng. Nu bär felet en
    stabil kod som ytan översätter (lib/leads/suite.ts), och texten är svensk
    som resten av API:t."""
    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug="kund-ab12cd34", name="Telefonibolaget")

    with pytest.raises(MissingBusinessContextError) as fel:
        await require_egen_produkt(storage, tenant["id"])

    assert fel.value.kod == SAKNAR_PRODUKT == "saknar_produkt"
    besked = str(fel.value)
    assert PLATS in besked
    assert "Iris does not" not in besked and "Leads › Produkter" not in besked


@pytest.mark.anyio
async def test_rader_utan_namn_raknas_inte_som_produkt():
    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug="kund-ab12cd34", name="Telefonibolaget")
    await storage.set_agent_settings(
        tenant["id"], agent_type="leads", settings={"produkter": [{"namn": "  ", "nytta": "x"}]}
    )
    with pytest.raises(MissingBusinessContextError):
        await require_egen_produkt(storage, tenant["id"])


@pytest.mark.anyio
async def test_med_en_produkt_passerar_spärren():
    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug="kund-ab12cd34", name="Telefonibolaget")
    await storage.set_agent_settings(
        tenant["id"],
        agent_type="leads",
        settings={"produkter": [{"namn": "Upphandling av företagstelefoni", "nytta": "lägre kostnad"}]},
    )
    produkter = await require_egen_produkt(storage, tenant["id"])
    assert [p["namn"] for p in produkter] == ["Upphandling av företagstelefoni"]


@pytest.mark.anyio
async def test_utkastet_stannar_fore_modellen_utan_produkt(live_llm):
    """Autopiloten, inkorgsleads och Skapa om utkast går inte genom
    körstarten. Spärren sitter därför också i utkaststeget, före modellen."""
    from unittest.mock import patch

    from app.agent.leads_research_v2 import run_outreach_draft_v2
    from tests.agent.test_leads_v2_wiring import _FakeLLM

    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug="kund-ab12cd34", name="Telefonibolaget")
    await storage.save_context_doc(
        tenant["id"],
        kind="product_marketing",
        content="Vi upphandlar företagstelefoni åt småföretag. " * 4,
        source="test",
    )
    prospect = await storage.create_prospect(tenant["id"], company_name="Exempelbolaget")
    thread = await storage.ensure_outreach_thread(tenant["id"], prospect_id=prospect["id"])
    llm = _FakeLLM()
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        with pytest.raises(MissingBusinessContextError) as fel:
            await run_outreach_draft_v2(
                storage,
                tenant["id"],
                thread_id=thread["id"],
                prospect_email="info@exempelbolaget.se",
                tenant_name="Telefonibolaget",
                company_name="Exempelbolaget",
                offer_summary="",
                context_pack="",
                brief="",
                research_summary='{"company_summary": "Svensk e-handel."}',
                is_test=True,
            )
    assert fel.value.kod == SAKNAR_PRODUKT
    assert llm.calls == []
    assert await storage.list_review_queue(tenant["id"]) == []


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_korning_med_utkast_stannar_vid_starten_utan_produkt(live_llm, monkeypatch):
    """Inget jobb, ingen research, ingen rad i kön: beskedet kommer i svaret
    på startklicket, där kunden startade körningen."""

    async def _text(*_a, **_k):
        return "Vad vi säljer: upphandling av företagstelefoni åt småföretag."

    monkeypatch.setattr(leads_api, "las_kundtext", _text)
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await storage.set_agent_settings(DEFAULT_TENANT_ID, agent_type="leads", settings={"produkter": []})
        async with _client() as client:
            svar = await client.post(
                "/api/leads/runs/batch",
                headers=DEMO,
                json={"limit": 3, "is_test": True, "scope": "research_and_draft"},
            )
            assert svar.status_code == 422, svar.text
            # Samma form som backendens andra besked ({"detail": {"message": …}}),
            # som proxyn (app/api/snajp-support/_lib.ts) gör till `error`.
            detalj = svar.json()["detail"]
            assert detalj["kod"] == "saknar_produkt"
            assert PLATS in detalj["message"]
        assert await storage.list_review_queue(DEFAULT_TENANT_ID) == []


@pytest.mark.anyio
async def test_korning_med_utkast_startar_med_produkt(live_llm, monkeypatch):
    async def _text(*_a, **_k):
        return "Vad vi säljer: upphandling av företagstelefoni åt småföretag."

    monkeypatch.setattr(leads_api, "las_kundtext", _text)
    async with app.router.lifespan_context(app):
        await app.state.storage.set_agent_settings(
            DEFAULT_TENANT_ID,
            agent_type="leads",
            settings={"produkter": [{"namn": "Upphandling av företagstelefoni", "nytta": "lägre kostnad"}]},
        )
        async with _client() as client:
            svar = await client.post(
                "/api/leads/runs/batch",
                headers=DEMO,
                json={"limit": 3, "is_test": True, "scope": "research_and_draft"},
            )
            assert svar.status_code == 202, svar.text
