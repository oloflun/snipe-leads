"""Två hål i Iris faktakontroll (Antons beställning 2026-11-16).

HÅL 1: researchens `research_evidence` byggdes av modellens egna anteckningar
(overifierad evidence, likely_pains, trigger_events) och gick till
grundningsgrindens TILLÅTNA fakta. Ett tal som researchmodellen hittade på
blev alltså godkänt i mejlet. Nu bär den bara det som bevisligen står i hämtat
material (verifierade citat, uppmätta webbsignaler).

HÅL 2: utkastet ändrades EFTER grinden (tilltal, bolagsnamn, ämnesraden ur
kundens lista, "upp till") och det som köades hade aldrig prövats. Nu prövas
den exakta texten som köas, och ett kvarstående ostött påstående går till
människa (INV-GROUND-001), aldrig till kön.

Samma princip som test_leads_v2_wiring.py: bara nätverksgränsen (LLM-klienten
och skrapningen) mockas, allt annat är den riktiga kodvägen.
"""

import json
from unittest.mock import patch

import pytest

from app.agent.leads_research_v2 import run_outreach_draft_v2, run_research_step_v2
from app.config import get_settings
from app.leads import erbjudanden, sparad_research
from app.storage.memory import MemoryStorage
from tests.agent.test_leads_v2_wiring import (
    TENANT,
    _fake_scrape,
    _FakeLLM,
    _prepare_outreach,
    _prepare_prospect,
)

pytestmark = pytest.mark.anyio

#: Talet som bara står i modellens egna anteckningar, aldrig i det hämtade
#: materialet, kontextpaketet eller erbjudandet.
PAHITT = "Returfrågorna minskade med 42 procent efter bytet"
BRODTEXT = (
    "Hej,\n\nMed fri retur på allt ni säljer blir returfrågorna många.\n\n"
    "Vår agent kan minska returfrågorna med 42 procent.\n\n"
    "Vill ni se hur räcker ett svar på mejlet."
)


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


# --- Hål 1 -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("falt", "varde"),
    [
        ("evidence", ["Fri retur inom 30 dagar", PAHITT]),
        ("likely_pains", [PAHITT]),
        ("trigger_events", [PAHITT]),
    ],
)
async def test_modellens_eget_tal_falls_av_grinden(falt, varde):
    """Talet står bara i ett av modellens fält: researchen och utkastet körs
    genom den riktiga kedjan, och utkastet som påstår talet köas inte."""
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    with (
        patch(
            "app.agent.step_runner.get_llm_client",
            return_value=_FakeLLM(overrides={"sa:account-research": {falt: varde}}),
        ),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
    ):
        research = await run_research_step_v2(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
        )

    # Underlaget som når grinden: bara det som står i materialet.
    assert not any("42" in rad for rad in research["research_evidence"])
    assert "Fri retur inom 30 dagar" in research["research_evidence"]
    # Modellens fält når fortfarande utkaststeget som underlag.
    assert "42 procent" in research["final_output"] or falt == "evidence"

    thread_id = await _prepare_outreach(storage)
    llm = _FakeLLM(
        overrides={
            "sa:draft-outreach": {"body": BRODTEXT},
            "snajp:humanizer-svenska": {"final_body": BRODTEXT},
        }
    )
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        result = await run_outreach_draft_v2(
            storage,
            TENANT,
            thread_id=thread_id,
            prospect_email="kundservice@exempelbolaget.se",
            tenant_name="Snajp",
            company_name="Exempelbolaget",
            offer_summary="Pilot på returfrågor",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
            research_summary=research["final_output"],
            research_evidence=tuple(research["research_evidence"]),
            is_test=True,
        )

    assert result["grounding"]["fired"] is True
    assert any("42" in rad for rad in result["grounding"]["unsupported_before"])
    assert result["queued"] is False
    assert result["escalated"] is True
    assert await storage.list_review_queue(TENANT) == []


async def test_sparad_research_bar_inte_modellens_anteckningar_till_grinden():
    """En körning före ändringen sparade de breda beläggen i underlagsposten.
    Skapa om utkast och uppföljningar läser posten, så de byggs om ur citaten."""
    storage = MemoryStorage()
    p = await storage.create_prospect(TENANT, company_name="Exempelbolaget")
    post = sparad_research.underlagspost(
        {
            "citat": ["Fri retur inom 30 dagar"],
            "likely_pains": [PAHITT],
            "research_evidence": ["Fri retur inom 30 dagar", PAHITT],
        }
    )
    await storage.log_agent_run(
        TENANT, agent_type="leads_research", pack_version="v", skills_used=[], input_text="",
        output_text="{}", step_log=[post], tokens_in=1, tokens_out=1, latency_ms=1, prospect_id=p["id"],
    )
    u = await sparad_research.las(storage, TENANT, p["id"])
    assert u["research_evidence"] == ["Fri retur inom 30 dagar"]
    assert u["likely_pains"] == [PAHITT]


# --- Hål 2 -------------------------------------------------------------------


async def _med_amnen(storage, amnen: list[str]) -> str:
    thread_id = await _prepare_outreach(storage)
    await storage.set_agent_settings(
        TENANT,
        agent_type="leads",
        settings={
            "erbjudanden": {
                "aktiva": [{"nyckel": "pilot", "vikt": 1}],
                "villkor": {"pilot": {"Supportagenten": "Kostnadsfri pilot i tre månader."}},
                "amnen": {"Supportagenten": amnen},
            }
        },
    )
    return thread_id


async def _utkast(storage, thread_id: str) -> dict:
    with patch("app.agent.step_runner.get_llm_client", return_value=_FakeLLM()):
        return await run_outreach_draft_v2(
            storage,
            TENANT,
            thread_id=thread_id,
            prospect_email="kundservice@exempelbolaget.se",
            tenant_name="Snajp",
            company_name="Exempelbolaget",
            offer_summary="Supportagenten: svarar på kundmejlen",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
            research_summary=json.dumps({"vald_produkt": {"namn": "Supportagenten", "nytta": "svar"}}),
            research_evidence=("Fri retur inom 30 dagar",),
            is_test=True,
        )


async def test_andring_efter_grinden_kan_inte_koa_ett_ostott_pastaende(monkeypatch):
    """Ämnesraden väljs i kod efter grinden. Bär den ett tal som inget
    underlag har, ska det fällas på den text som köas, inte passera."""
    storage = MemoryStorage()
    thread_id = await _med_amnen(storage, ["Support dygnet runt för dina kunder"])
    monkeypatch.setattr(erbjudanden, "valj_amne", lambda rader, nyckel, *, du: "Spara 37 % på returerna")

    result = await _utkast(storage, thread_id)

    assert result["queued"] is False
    assert result["escalated"] is True
    assert result["grounding"]["ok"] is False
    assert any("37" in rad for rad in result["grounding"]["unsupported_after"])
    assert "Faktagrinden" in (result["escalation_reason"] or "")
    assert await storage.list_review_queue(TENANT) == []


async def test_kundens_egen_amnesrad_med_tal_koas_fortfarande():
    """Kundens ämnesrader är kundens eget underlag: "Support 24/7 för dina
    kunder" ska inte fällas på 24 och 7 när ämnesraden nu grindas."""
    storage = MemoryStorage()
    thread_id = await _med_amnen(storage, ["Support 24/7 för dina kunder"])

    result = await _utkast(storage, thread_id)

    assert result["queued"] is True, result["escalation_reason"]
    assert result["subject"] == erbjudanden.till_ni("Support 24/7 för dina kunder")
