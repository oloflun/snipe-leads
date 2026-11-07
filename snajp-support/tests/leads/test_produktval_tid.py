"""Produktvalet efter vad som tar mest tid hos bolaget (Anton 2026-11-07).

"Satsa på support för fastighetsbolag och leads för bygg, se till att agenten
bättre kan avgöra detta själv utifrån vad som rimligtvis tar mest tid av
företaget och vilken produkt som bäst täcker detta." Provet samma dag gav ett
fastighetsbolag Iris och ett mejl om "nya hyresgäster". Researchen skriver nu
tar_mest_tid före produkten och väljer den produkt som täcker det; skälet
följer med till utkastet. Testerna låser uppgiften, Snajps regel och att fältet
når utkastets underlag.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from app.agent import leads_research_v2 as v2
from app.leads import sparad_research
from app.storage.memory import MemoryStorage
from tests.agent.test_leads_v2_wiring import (  # noqa: F401 — fixturen används via autouse
    TENANT,
    _FakeLLM,
    _RESEARCH_SVAR,
    _fake_scrape,
    _fake_deepseek_key,
    _prepare_prospect,
)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import snajp_malgrupp as sm  # noqa: E402

@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_researchen_skriver_tar_mest_tid_fore_produkten():
    uppgift = v2._RESEARCH_V2_UPPGIFT
    assert "tar_mest_tid" in uppgift
    assert uppgift.index("tar_mest_tid") < uppgift.index("produkt (namnet på")
    overlay = (ROOT / "agent-core" / "overlays" / "leads-research-v2.md").read_text(encoding="utf-8")
    assert overlay.index("`tar_mest_tid`") < overlay.index("- `produkt`")


@pytest.mark.parametrize("produktval", [v2._PRODUKTVAL, v2._PRODUKTVAL_BEHOV])
def test_produktvalet_vager_vad_som_tar_mest_tid(produktval):
    assert v2._TIDSVAL in produktval
    # Ärenden från hyresgäster och kunder mot att hitta nästa kund, och kundens
    # egna instruktioner går före.
    assert "fastighetsbolag" in v2._TIDSVAL and "hyresgäster" in v2._TIDSVAL
    assert "bygg" in v2._TIDSVAL and "hitta nästa kund" in v2._TIDSVAL
    assert "bäst täcker" in v2._TIDSVAL
    assert "Kundens egna instruktioner om produktvalet gäller före" in v2._TIDSVAL


def test_snajps_regel_fastighet_far_support_och_bygg_far_iris():
    rad = next(r for r in sm.IRIS_INSTRUKTION.splitlines() if r.startswith("- Produktvalet"))
    assert "fastighetsbolag" in rad and "Supportagenten" in rad
    assert "byggföretag" in rad and "Iris" in rad
    assert rad.index("fastighetsbolag") < rad.index("Supportagenten") < rad.index("byggföretag") < rad.index("Iris")


def test_skalet_foljer_med_till_utkastets_underlag():
    assert "tar_mest_tid" in sparad_research.UNDERLAGSFALT
    post = sparad_research.underlagspost({"tar_mest_tid": "Hyresgästernas felanmälningar."})
    assert post["tar_mest_tid"] == "Hyresgästernas felanmälningar."
    vy = json.loads(v2._utkastens_researchvy(json.dumps({"tar_mest_tid": "Hyresgästernas felanmälningar.",
                                                         "company_summary": "Förvaltar hyresfastigheter."})))
    assert vy["tar_mest_tid_hos_dem"] == "Hyresgästernas felanmälningar."


@pytest.mark.anyio
async def test_researchen_returnerar_och_sparar_skalet():
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    await storage.set_agent_settings(
        TENANT,
        agent_type="leads",
        settings={"produkter": [{"namn": "Supportagenten", "nytta": "svarar på kundfrågor"},
                                {"namn": "Iris, leadsagenten", "nytta": "hittar nya företagskunder"}]},
    )
    svar = {**_RESEARCH_SVAR, "tar_mest_tid": "Att svara på kundernas returfrågor.", "produkt": "Supportagenten"}
    llm = _FakeLLM({"sa:account-research": svar})
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
    ):
        result = await v2.run_research_step_v2(
            storage, TENANT, prospect_id=prospect_id, tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: svensk e-handel.", brief="", is_test=True,
        )
    assert result["tar_mest_tid"] == "Att svara på kundernas returfrågor."
    assert (result["produkt"] or {}).get("namn") == "Supportagenten"
    # Uppgiften till modellen bär tidsvalet när kunden har produkter.
    assert v2._TIDSVAL in llm.user_messages[0]
    underlag = await sparad_research.las(storage, TENANT, prospect_id)
    assert underlag and underlag["tar_mest_tid"] == "Att svara på kundernas returfrågor."
