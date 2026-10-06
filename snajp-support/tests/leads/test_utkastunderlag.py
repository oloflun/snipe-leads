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


def test_mottagaren_ar_bolagets_kontaktmejl():
    """Sebbes beslut 2026-10-07: det enda kravet är en kontaktmejl till
    bolaget som utkastet kan nå fram till. Personens adress föredras i
    urvalet, men info@/kontakt@ på bolagets domän duger. Aldrig en privat
    adress, en främmande domän eller en HR-, ekonomi- eller robotadress."""
    vd = {"contact_name": "Adam Wartecki", "contact_role": "VD", "website": "https://prestigo.se"}
    assert vd_mottagare({**vd, "contact_email": "adam@prestigo.se"}) == "adam@prestigo.se"
    assert vd_mottagare({**vd, "contact_email": "info@prestigo.se"}) == "info@prestigo.se"
    assert vd_mottagare({"website": "https://prestigo.se", "contact_email": "kontakt@prestigo.se"}) == "kontakt@prestigo.se"
    for fel in ("rekrytering@prestigo.se", "noreply@prestigo.se", "faktura@prestigo.se", "adam@gmail.com", "info@annat.se"):
        assert vd_mottagare({**vd, "contact_email": fel}) is None, fel
    assert vd_mottagare({**vd, "contact_email": None}) is None


def test_bolagsadressen_plockas_ur_sidan():
    from app.leads.discovery import bolagsadress_i_text

    sida = '<p>Jobba hos oss: <a href="mailto:jobb@alfa.se">jobb</a></p><footer>Kontakt: info (at) alfa (punkt) se</footer>'
    assert bolagsadress_i_text(sida, "https://www.alfa.se") == "info@alfa.se"
    assert bolagsadress_i_text("Skriv till hej@gmail.com", "https://alfa.se") is None
    assert bolagsadress_i_text("Kontakt: sales@alfa.se eller info@alfa.se", "https://alfa.se") == "sales@alfa.se"


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


async def test_bedomningens_belagg_racker_som_citat_nar_evidence_ar_tom():
    """Verifieringskörningen 2026-10-07: tre leverbara leads, noll utkast,
    eftersom modellen lämnade evidence tom fast produktmatchningen stod på
    ett ordagrant citat. Bedömningens belägg räknas, med samma kontroll."""
    storage = MemoryStorage()
    prospect_id = await _prepare_prospect(storage)
    llm = _FakeLLM(overrides={"sa:account-research": {
        "qualified": True,
        "evidence": [],
        "bedomningar": [
            {"kriterie_id": "kp", "utslag": "ja", "resonemang": "Returer.",
             "belagg": [{"url": "u", "citat": "Fri retur inom 30 dagar."}, {"url": "u", "citat": "Påhittat citat."}]},
        ],
    }})
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch("app.agent.leads_agent._scrape_registered_source_impl", new=_fake_scrape()),
    ):
        result = await run_research_step_v2(
            storage, TENANT, prospect_id=prospect_id, tenant_name="Snajp",
            context_pack="## Kontextpaket\nICP: e-handel.", brief="", is_test=True, profil={"version": "t"},
        )
    assert result["citat"] == ["Fri retur inom 30 dagar."]


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


def test_platshallare_och_pahittat_tilltal_nar_aldrig_kon():
    """Mätningen 2026-10-06: "Hej Mikael," (påhittat) och "Hej [VD:ns
    förnamn]," (mallfält) i köade utkast."""
    from app.leads.grounding_gate import build_permitted_facts, check_grounding
    from app.leads.tilltal import ratta_tilltal

    fakta = build_permitted_facts(context_pack="Snajp", research_evidence=(), offer_summary="", brief="",
                                  tenant_name="Snajp", company_name="Smålands Stålhallar AB")
    dom = check_grounding("Hej {förnamn},\nVi ses [datum].", fakta)
    assert not dom.ok and {c.kind for c in dom.unsupported} == {"placeholder"}
    assert ratta_tilltal("Hej Mikael,\nJag såg", "Jonas Ek").startswith("Hej Jonas,")
    assert ratta_tilltal("Hej [VD:ns förnamn],\nJag såg", None).startswith("Hej,")


def test_person_kontakt_rangordnar_vd_chef_ansvarig_anstalld():
    """Sebbes revidering 2026-10-07: bästa NAMNGIVNA kontakt vinner — VD
    före chef, chef före namngiven anställd. Beviset är detsamma som för
    VD: namnet står intill adressen och lokaldelen bär namnet."""
    from app.leads.discovery import person_kontakt_i_text

    sida = (
        "<h2>Kontakt</h2>"
        "<p>Lisa Lind, Säljare — lisa@bolaget.se</p>"
        "<p>Per Palm, Försäljningschef — per@bolaget.se</p>"
        "<p>Eva Ek, VD — eva@bolaget.se</p>"
        "<p>Info — info@bolaget.se</p>"
    )
    basta = person_kontakt_i_text(sida, "https://bolaget.se")
    assert (basta["contact_name"], basta["contact_email"]) == ("Eva Ek", "eva@bolaget.se")
    assert basta["rang"] == 0

    utan_vd = person_kontakt_i_text(sida.replace("Eva Ek, VD — eva@bolaget.se", ""), "https://bolaget.se")
    assert (utan_vd["contact_name"], utan_vd["rang"]) == ("Per Palm", 1)
    assert "chef" in utan_vd["contact_role"].lower()

    bara_anstalld = person_kontakt_i_text(
        "<p>Lisa Lind — lisa@bolaget.se</p><p>info@bolaget.se</p>", "https://bolaget.se"
    )
    assert (bara_anstalld["contact_name"], bara_anstalld["contact_role"], bara_anstalld["rang"]) == (
        "Lisa Lind", None, 2)

    # En funktionsadress utan namn intill ger INGEN kontakt — hellre tomt än gissat.
    assert person_kontakt_i_text("<p>Kontakta oss: info@bolaget.se</p>", "https://bolaget.se") is None


def test_mailto_och_obfuskerade_adresser_skordas():
    """Körningarna 2026-10-07: 8 bolag med sajt, 0 styrkta kontakter — för
    att adressen bara låg i mailto-länken (taggstrippen åt den) eller var
    utskriven som "eva (at) bolaget (punkt) se"."""
    from app.leads.discovery import person_kontakt_i_text, vd_uppgift_i_text

    mailto = '<p><a href="mailto:eva.ek@bolaget.se">Eva Ek</a>, VD</p>'
    traff = person_kontakt_i_text(mailto, "https://bolaget.se")
    assert (traff["contact_name"], traff["contact_email"], traff["rang"]) == ("Eva Ek", "eva.ek@bolaget.se", 0)
    # VD-varianten (listspåret) har kvar sitt tvåledskrav på >=3 tecken,
    # så den provas med ett längre namn — mailto-skörden är poängen här.
    vd_mailto = '<p><a href="mailto:eva.ekberg@bolaget.se">Eva Ekberg</a>, VD</p>'
    assert vd_uppgift_i_text(vd_mailto, "Eva Ekberg", "https://bolaget.se") == {
        "contact_email": "eva.ekberg@bolaget.se", "contact_phone": None}

    obfuskerat = "<p>Per Palm, Platschef: per (at) bolaget (punkt) se</p>"
    traff = person_kontakt_i_text(obfuskerat, "https://bolaget.se")
    assert (traff["contact_name"], traff["contact_email"], traff["rang"]) == ("Per Palm", "per@bolaget.se", 1)


def test_utkastet_kallar_bolaget_vid_kortnamn():
    """Utkasten 2026-10-07 bar registernamnet i ämnesraden ("… Linnéstaden
    Bygg & Service Aktiebolag") och VERSALNAMN ur registret. Bolagsformen tas
    bort i kod, modellens egen stavning av namnet står kvar."""
    from app.leads.tilltal import korta_bolagsnamn, kortnamn

    assert kortnamn("Roy Johnsson Linnéstaden Bygg & Service Aktiebolag") == (
        "Roy Johnsson Linnéstaden Bygg & Service"
    )
    assert kortnamn("HÄRLANDA FOG & BYGGSERVICE AB") == "Härlanda Fog & Byggservice"
    assert kortnamn("Volvo AB (publ)") == "Volvo"
    assert kortnamn("AB") == "AB", "blir inget kvar står originalet"
    assert (
        korta_bolagsnamn(
            "Bygg i Göteborg – Roy Johnsson Linnéstaden Bygg & Service Aktiebolag",
            "Roy Johnsson Linnéstaden Bygg & Service Aktiebolag",
        )
        == "Bygg i Göteborg – Roy Johnsson Linnéstaden Bygg & Service"
    )
    assert (
        korta_bolagsnamn("Jag såg att Tolered Snickeri & Bygg AB gör kök.", "Tolered snickeri & bygg AB")
        == "Jag såg att Tolered Snickeri & Bygg gör kök."
    )
    # "AB" som början på ett ord är inte bolagsformen.
    assert korta_bolagsnamn("Volvo Abisko", "Volvo AB") == "Volvo Abisko"
