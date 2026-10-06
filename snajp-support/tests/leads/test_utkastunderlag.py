"""Utkasten: rätt mottagare, rätt erbjudande, riktigt underlag, inga påhittade case.

Provkörningen 2026-10-05 (Snajp) gav utkast till rekrytering@ och till en
inköpschef, mejl som räknade upp alla tre agenterna, öppningar som "Jag såg
att ni ligger i Göteborg" och ett påhittat case: "Den hjälpte nyligen ett
annat byggföretag i Göteborg".
"""

from unittest.mock import patch

import pytest

from app.agent.leads_agent import _uppgradera_kontakt
from app.agent.leads_research_v2 import _utkastens_researchvy, las_produkter, run_research_step_v2
from app.config import get_settings
from app.leads.discovery import ar_vd, vd_mottagare
from app.leads.grounding_gate import build_permitted_facts, check_grounding
from app.storage.memory import MemoryStorage
from tests.agent.test_leads_v2_wiring import TENANT, _FakeLLM, _fake_scrape, _prepare_prospect

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Mottagaren -------------------------------------------------------------


def test_bara_vd_med_adress_som_bar_namnet():
    vd = {"contact_name": "Adam Wartecki", "contact_role": "VD", "website": "https://prestigo.se"}
    assert vd_mottagare({**vd, "contact_email": "adam@prestigo.se"}) == "adam@prestigo.se"
    assert vd_mottagare({**vd, "contact_email": "a.wartecki@prestigo.se"}) == "a.wartecki@prestigo.se"
    assert vd_mottagare({**vd, "contact_email": "info@prestigo.se"}) is None
    assert vd_mottagare({**vd, "contact_email": "rekrytering@prestigo.se"}) is None
    assert vd_mottagare({**vd, "contact_role": "Inköpschef", "contact_email": "adam@prestigo.se"}) is None
    assert vd_mottagare({**vd, "contact_email": "adam@gmail.com"}) is None


def test_vd_i_de_former_den_star_pa_sajter():
    for roll in ("VD", "vd & grundare", "Verkställande direktör", "CEO och grundare"):
        assert ar_vd(roll), roll
    for roll in ("Inköpschef", "Platschef", "Ekonomiansvarig", ""):
        assert not ar_vd(roll), roll


async def test_funktionsadress_fasts_aldrig_pa_en_namngiven_person():
    storage = MemoryStorage()
    prospekt = await storage.create_prospect(TENANT, company_name="BRA AB", profil={"website": "https://bragroup.se"})
    await _uppgradera_kontakt(
        storage, TENANT, prospekt["id"], prospect=await storage.get_prospect(TENANT, prospekt["id"]),
        fynd={"contact_name": "Anna Berg", "contact_role": "VD"},
        material="Anna Berg, VD. Jobba hos oss: rekrytering@bragroup.se",
    )
    rad = await storage.get_prospect(TENANT, prospekt["id"])
    assert rad["contact_name"] == "Anna Berg"
    assert not rad.get("contact_email")


# -- Faktagrinden -----------------------------------------------------------

_FAKTA = dict(context_pack="Snajp säljer AI-agenter.", offer_summary="Iris hittar kunder.", research_evidence=(),
              brief="", tenant_name="Snajp", company_name="F O Peterson")


def test_onamngivet_case_falls_nar_underlaget_saknar_case():
    fakta = build_permitted_facts(**_FAKTA)
    for mening in (
        "Den hjälpte nyligen ett annat byggföretag i Göteborg att snabbt hitta kompetens.",
        "Vi kan visa hur vi har hjälpt liknande företag att öka sin kundbas.",
        "Vi har erfarenhet av att effektivisera leadgenerering för liknande företag.",
    ):
        dom = check_grounding(mening, fakta)
        assert not dom.ok and dom.unsupported[0].kind == "unnamed_case", mening
    assert check_grounding("Många företag i er bransch kämpar med att hitta nya projekt.", fakta).ok


def test_onamngivet_case_slapps_nar_kundens_underlag_bar_ett():
    fakta = build_permitted_facts(**{**_FAKTA, "context_pack": "Vi har hjälpt flera byggföretag att hitta kunder."})
    assert check_grounding("Vi har hjälpt liknande företag.", fakta).ok


# -- Researchen: produktval och citat --------------------------------------

_PRODUKTER = [
    {"namn": "Supportagenten", "nytta": "svarar på kundfrågor dygnet runt"},
    {"namn": "Iris", "nytta": "hittar och kvalificerar nya kunder"},
]


def test_produktlistan_rensas():
    assert las_produkter({"produkter": [*_PRODUKTER, {"namn": " "}, "fel"]}) == _PRODUKTER
    assert las_produkter({}) == []


@pytest.fixture(autouse=True)
def _fake_deepseek_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_researchen_valjer_en_produkt_och_behaller_bara_citat_som_star_pa_sidan():
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    await storage.set_agent_settings(TENANT, agent_type="leads", settings={"produkter": _PRODUKTER})
    llm = _FakeLLM(overrides={"sa:account-research": {
        "qualified": True, "produkt": "supportagenten",
        "evidence": ["Fri retur inom 30 dagar.", "Vi har 400 butiker i Norden."],
    }})
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
    ):
        result = await run_research_step_v2(
            storage, TENANT, prospect_id=prospect_id, tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: e-handel.", brief="", is_test=True, profil={"version": "t"},
        )
    assert result["produkt"] == _PRODUKTER[0]
    assert result["citat"] == ["Fri retur inom 30 dagar."]
    assert "Supportagenten: svarar på kundfrågor dygnet runt" in llm.user_messages[0]
    assert "PRODUKTVAL" in llm.user_messages[0]


def test_utkastet_far_mottagare_produkt_och_citat_forst():
    import json

    vy = json.loads(_utkastens_researchvy(json.dumps({
        "company_summary": "Bygger moduler.",
        "citat": ["Vi bygger moduler i trä."],
        "lagesbeskrivning": "Bolaget har öppnat en ny fabrik.",
        "mottagare": {"namn": "Anna Berg", "roll": "VD"},
        "vald_produkt": _PRODUKTER[1],
    })))
    assert list(vy)[:4] == ["mottagare", "vald_produkt", "citat_ur_bolagets_sidor", "lagesbeskrivning"]
