"""Rangpoängen skiljer godkända leads åt (Sebbe 2026-10-07).

Grindens poäng var 100 för alla 32 synliga leads i Snajps development:
varje nej fäller redan bolaget, så ett synligt lead har klarat allt.
score_total mäter nu hur bra ett godkänt lead är; grinden står orörd.
"""

from unittest.mock import patch

import pytest

from app.agent.leads_research_v2 import run_research_step_v2
from app.config import get_settings
from app.leads import rangpoang as r
from app.storage.memory import MemoryStorage
from tests.agent.test_leads_v2_wiring import TENANT, _FakeLLM, _fake_scrape, _prepare_prospect


def test_starkt_lead_slar_svagt():
    r.demo()


def test_namngiven_adress_kraver_namnet_i_lokaldelen():
    assert r.namngiven_adress({"contact_name": "Åsa Öberg", "contact_email": "asa@bolag.se"})
    assert not r.namngiven_adress({"contact_name": "Åsa Öberg", "contact_email": "info@bolag.se"})
    assert not r.namngiven_adress({"contact_email": "info@bolag.se"})


def test_vikterna_summerar_till_hundra():
    assert sum(r.VIKT.values()) == 100
    perfekt = {
        "jev": {"triage": {"fit": 3}},
        "score_breakdown": [{"belagg": [{"citat": "x"}] * 5}],
        "contact_name": "Per Ek",
        "contact_email": "per.ek@bolag.se",
        "signaler": ["a", "b"],
    }
    assert r.rangpoang(perfekt) == 100
    assert r.rangpoang({}) == round(r.VIKT["passform"] * r.PASSFORM_OKAND)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_researchen_sparar_rangpoangen_inte_grindens(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    try:
        storage = MemoryStorage()
        prospect_id = await _prepare_prospect(storage)
        kp = {"kriterie_id": "kp", "utslag": "ja", "resonemang": "Kan använda produkten.",
              "belagg": [{"url": "https://exempelbolaget.se", "citat": "Exempelbolaget"}]}
        llm = _FakeLLM(overrides={"sa:account-research": {"qualified": True, "bedomningar": [kp]}})
        with (
            patch("app.agent.step_runner.get_llm_client", return_value=llm),
            patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
        ):
            result = await run_research_step_v2(
                storage, TENANT, prospect_id=prospect_id, tenant_name="Snajp",
                context_pack="## Kontextpaket\nICP: svensk e-handel.", brief="", is_test=True,
            )
        rad = await storage.get_prospect(TENANT, prospect_id)
    finally:
        get_settings.cache_clear()
    assert result["qualified"] and rad["niva"] in ("A", "B")
    assert rad["score_total"] == r.rangpoang(rad) < 100
    # Grinden är orörd: träffsäkerheten (kundens tröskel) är kvar på 1.0.
    assert rad["icp_fit"] == 1.0
