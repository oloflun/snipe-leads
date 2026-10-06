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


async def _kor(
    overrides: dict, *, sida: str | None = None, icp: dict | None = None, profil: dict | None = None
) -> dict:
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
            profil=profil,
        )


#: En profil med ETT måste-kriterium. Sedan 2026-09-30 fäller bara profilens
#: kriterier (INV-LEADS-PROFIL-001) — modellens fria `qualified` avgör inget.
_PROFIL = {
    "version": "test",
    "kriterier": [
        {"id": "k1", "text": "Säljer kläder online", "krav": "maste", "vikt": 3, "belagg": "kalltext"}
    ],
    "uteslut": [{"text": "bemannings- eller rekryteringsföretag", "kallmening": ""}],
}


async def test_underkant_bolag_stoppas_fore_utkastet():
    result = await _kor(
        {"bedomningar": [{"kriterie_id": "k1", "utslag": "nej", "resonemang": "Säljer returtjänster.",
                          "belagg": [{"url": "https://exempelbolaget.se", "citat": "Fri retur inom 30 dagar"}]}]},
        profil=_PROFIL,
    )
    assert result["qualified"] is False
    assert result["niva"] == "C"
    assert result["stopped_early"] == "ej_kvalificerad"


async def test_modellens_fria_underkannande_faller_inte_utan_profilkriterium():
    """Alunix 2026-09-29: 'Juristbyråer är inte målgruppen' fällde ett bolag
    fast profilen inte nämnde bransch. Ett fritt qualified=false utan utslag
    på ett profilkriterium får inte fälla."""
    result = await _kor({"qualified": False, "disqualifiers": ["Fel bransch"]}, profil=_PROFIL)
    assert result["qualified"] is True
    assert result["niva"] == "B"
    assert result["motivering"]


async def test_nej_utan_verifierat_citat_faller_inte():
    result = await _kor(
        {"bedomningar": [{"kriterie_id": "k1", "utslag": "nej", "resonemang": "Gissning.",
                          "belagg": [{"citat": "står inte på sidan"}]}]},
        profil=_PROFIL,
    )
    assert result["qualified"] is True


async def test_kvalificerat_bolag_utan_kontaktvag_stoppas():
    result = await _kor(
        {"qualified": True, "contact_email": None, "contact_name": None},
        sida="# Exempelbolaget\nFri retur inom 30 dagar. Ingen adress här.",
    )
    assert result["stopped_early"] == "kontakt_saknas"


async def test_utan_kallmaterial_gors_inget_modellanrop_och_inget_blir_redo():
    """Provkörningen 2026-10-05: tre påhittade bolag gick genom researchen på
    raden "(inget källmaterial kunde hämtas)" och kom ut med poäng 100, status
    Redo och ett utkast."""
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    llm = _FakeLLM(overrides={"sa:account-research": {"qualified": True, "ort": "Göteborg"}})
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape("")),
    ):
        result = await run_research_step_v2(
            storage, TENANT, prospect_id=prospect_id, tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: svensk e-handel.", brief="", is_test=True,
            profil={"version": "test", "kommuner": ["Göteborg"]},
        )
    assert llm.calls == [], "inget underlag ska inte kosta ett modellanrop"
    assert result["stopped_early"] == "inget_underlag"
    assert result["qualified"] is False and result["niva"] == "C" and result["score_total"] == 0
    assert (await storage.get_prospect(TENANT, prospect_id)).get("status") != "ready"


async def test_webbmatningen_kors_bara_for_kunder_med_webbkriterium(monkeypatch):
    """Ett mejl från Snajp öppnade med "Er webbplats är byggd med Next.js":
    mätningen som byggdes åt webbyråerna kördes för alla kunder."""
    matt: list[str] = []

    async def _mat(url):
        matt.append(url)
        return {"har_webbplats": True, "url": url, "matt": True, "rader": ["Webbplatsen är byggd med Next.js."]}

    monkeypatch.setattr("app.leads.webbsignal.mat_webbplats", _mat)

    utan = await _kor({"qualified": True}, profil=_PROFIL)
    assert matt == []
    assert utan["webbsignaler"] == []
    assert not any("Next.js" in rad for rad in utan["research_evidence"])

    webbprofil = {
        **_PROFIL,
        "kriterier": [{"id": "k1", "text": "Gammal hemsida", "krav": "bor", "vikt": 2, "belagg": "webbsignal"}],
    }
    med = await _kor({"qualified": True}, profil=webbprofil)
    assert len(matt) == 1
    assert "Webbplatsen är byggd med Next.js." in med["webbsignaler"]


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


async def test_bemanning_falls_bara_via_profilens_uteslutning():
    sida = "# Exempelbolaget\nVi hyr ut IT-konsulter till kunder.\nKontakta oss: kundservice@exempelbolaget.se"
    svar = {"bedomningar": [{"kriterie_id": "u1", "utslag": "ja", "resonemang": "Hyr ut konsulter.",
                             "belagg": [{"citat": "Vi hyr ut IT-konsulter till kunder."}]}]}
    med = await _kor(svar, sida=sida, profil=_PROFIL)
    assert med["stopped_early"] == "ej_kvalificerad"
    utan = await _kor(svar, sida=sida, profil={**_PROFIL, "uteslut": []})
    assert utan["stopped_early"] is None


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
