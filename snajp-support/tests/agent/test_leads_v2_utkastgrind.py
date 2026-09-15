"""V2-researchen sätter stopped_early som V1 - annars får underkända bolag utkast.

Batch-vägen (api/leads.py, _run_batch_prospect) hoppar över utkastet bara
när stopped_early är satt. V2 returnerade `None` hårdkodat, och i
QA-kundens körning 2026-09-15 hamnade mejlutkast till bolag med
qualified=false i granskningskön.
"""

from unittest.mock import patch

import pytest

from app.agent.leads_research_v2 import run_research_step_v2
from app.config import get_settings
from app.storage.memory import MemoryStorage
from tests.agent.test_leads_v2_wiring import TENANT, _FakeLLM, _fake_scrape, _prepare_prospect

pytestmark = pytest.mark.anyio


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


async def _kor(overrides: dict, *, sida: str | None = None, icp: dict | None = None) -> dict:
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    llm = _FakeLLM(overrides={"sa:account-research": overrides})
    skrap = _fake_scrape(sida) if sida is not None else _fake_scrape()
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=skrap),
    ):
        return await run_research_step_v2(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
            is_test=True,
            icp=icp,
        )


async def test_underkant_bolag_stoppas_fore_utkastet():
    result = await _kor({"qualified": False, "icp_fit": 0.1, "disqualifiers": ["Antal anställda överstiger 49"]})
    assert result["qualified"] is False
    assert result["stopped_early"] == "ej_kvalificerad"


async def test_kvalificerat_bolag_utan_kontaktvag_stoppas():
    result = await _kor(
        {"qualified": True, "contact_email": None, "contact_name": None},
        sida="# Exempelbolaget\nFri retur inom 30 dagar. Ingen adress här.",
    )
    assert result["stopped_early"] == "kontakt_saknas"


async def test_kvalificerat_bolag_med_kontakt_gar_vidare():
    result = await _kor({"qualified": True})
    assert result["stopped_early"] is None


_NORDFORM = {
    "industries": ["IT-konsulter", "redovisningsbyråer"],
    "size": {"anstallda_min": 10, "anstallda_max": 49},
}


async def test_kodgrinden_faller_kand_storlek_over_taket_fore_utkastet():
    result = await _kor({"qualified": True, "icp_fit": 0.8, "antal_anstallda": 250}, icp=_NORDFORM)
    assert result["qualified"] is False
    assert result["stopped_early"] == "ej_kvalificerad"
    assert result["icp_fit"] <= 0.3


async def test_kodgrinden_faller_bemanningsforetag_fore_utkastet():
    result = await _kor({"qualified": True, "icp_fit": 0.7, "ar_bemanningsforetag": True}, icp=_NORDFORM)
    assert result["stopped_early"] == "ej_kvalificerad"


async def test_regeln_okant_ar_inte_fel_nar_modellen():
    """Mätt 2026-09-15: Spoon Agency fälldes med 'Antal anställda okänt' trots
    overlayens regel. Regeln ska stå i det modellen faktiskt får."""
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    llm = _FakeLLM()
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
    ):
        await run_research_step_v2(
            storage,
            TENANT,
            prospect_id=prospect_id,
            tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: svensk e-handel.",
            brief="",
            is_test=True,
        )
    fick = llm.system_prompts[0] + llm.user_messages[0]
    assert "OKÄNT ÄR INTE FEL" in fick
    assert "missing_information" in fick


async def test_okand_storlek_stoppar_inte():
    result = await _kor({"qualified": True, "antal_anstallda": None}, icp=_NORDFORM)
    assert result["stopped_early"] is None
