"""INV-LEADS-SCORE-001 + INV-LEADS-PROFIL-001 — mot den riktiga V2-researchen.

SCORE-001: efter research har prospektraden alltid score_total, minst en
score_breakdown-rad med motivering, en icke-tom motivering och en nivå —
oavsett vad modellen svarar (Alunix 2026-09-29: "—" och "Ingen
poängmotivering sparad.").

PROFIL-001: bara profilens kriterier fäller. Modellens fria qualified=false
och påhittade disqualifiers ("Juristbyråer är inte en del av målgruppen")
får aldrig göra det.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agent.leads_research_v2 import run_research_step_v2
from app.config import get_settings
from app.storage.memory import MemoryStorage
from tests.agent.test_leads_v2_wiring import TENANT, _FakeLLM, _fake_scrape, _prepare_prospect

pytestmark = pytest.mark.anyio

PROFIL = {
    "version": "inv",
    "kommuner": ["Göteborg"],
    "kriterier": [
        {"id": "k1", "text": "Gammal eller ingen hemsida", "krav": "maste", "vikt": 3, "belagg": "webbsignal"}
    ],
    "uteslut": [],
}

MODELLSVAR = [
    {},  # tomt svar
    {"qualified": False, "disqualifiers": ["Juristbyråer är inte en del av målgruppen"]},
    {"bedomningar": "inte en lista", "motivering": None},
    {"bedomningar": [{"kriterie_id": "k9", "utslag": "ja"}]},  # okänt kriterium
]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _nyckel(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _kor(svar: dict) -> tuple[dict, dict]:
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    llm = _FakeLLM(overrides={"sa:account-research": svar})
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
    ):
        result = await run_research_step_v2(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="## Kontextpaket",
            brief="",
            is_test=True,
            profil=PROFIL,
        )
    return result, await storage.get_prospect(TENANT, prospect_id)


@pytest.mark.parametrize("svar", MODELLSVAR)
async def test_poang_och_motivering_sparas_alltid(svar):
    result, rad = await _kor(svar)
    assert isinstance(rad["score_total"], int)
    assert rad["score_breakdown"] and all(r.get("motivering") for r in rad["score_breakdown"])
    assert (rad.get("motivering") or "").strip()
    assert rad["niva"] in ("A", "B", "C")
    assert rad["profil_version"] == "inv"
    assert result["motivering"] == rad["motivering"]


async def test_modellens_fria_omdome_faller_aldrig():
    result, rad = await _kor(MODELLSVAR[1])
    assert result["qualified"] is True
    assert rad["niva"] == "B"
    assert "Jurist" not in " ".join(rad.get("disqualifiers") or [])
