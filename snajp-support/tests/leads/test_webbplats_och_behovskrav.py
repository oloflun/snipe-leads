"""Webbplatskravet och behovskravet (Sebbe 2026-10-30, Snajp).

Snajp ville att Iris väljer bolag med upp till 200 anställda, även utan
webbplats, så länge det är ett riktigt företag som behöver kunder. Två
kundval bär det (agent_configs.settings, leads/profil.kundval):

* `webbplats_kravs: false` — registrets bolags-e-post räcker för Iris utan
  sajt (merinfo.fordela), och registrets bolagsfakta blir källmaterial
  (allabolag.registerfakta i researchen).
* `behov` — avgör produktmatchningen (kp) i stället för frågan om bolaget
  kan köpa produkten, som fällde 256 av Snajps 365 bortvalda.

Utan valen beter sig allt som förut. Inga nätanrop: MemoryStorage och
mockade källor.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.config import get_settings
from app.leads import katalog
from app.leads.bedomning import bedom
from app.leads.profil import (
    PRODUKTMATCH,
    indata_hash,
    kompilera,
    kundval,
    produktmatch_text,
    render_profil,
    tom_profil,
)
from app.leads.sources import allabolag
from app.leads.sources import merinfo as m
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-0000000f0e01"
BEHOV = "Ett riktigt, verksamt företag som behöver kunder för att driva verksamheten framåt"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _kandidat(**andring) -> dict:
    k = {
        "company_name": "Hagmans Tak AB",
        "orgnr": "556000-0101",
        "website": None,
        "ort": "Göteborg",
        "vd_namn": "Test Testsson",
        "anstallda": 15,
        "_epost": "kontor@hagmanstak.se",
        "_telefon": "031-12 34 56",
        "_bolagsform": "Aktiebolag",
        "source_name": "allabolag",
        "source_url": "https://www.allabolag.se/5560000101",
    }
    return {**k, **andring}


# -- Fördelningen ---------------------------------------------------------------


def test_utan_sajt_med_registrets_epost_blir_iris_bara_nar_sajt_inte_kravs():
    # Förvalet är oförändrat: utan sajt aldrig Iris (2026-10-15), telefonen
    # ger ringlistan.
    assert m.fordela(_kandidat(), None) == ("ring", None)
    assert m.fordela(_kandidat(_telefon=None), None) == ("ej_kvalificerad", "Utan webbplats")
    # Kunden kräver ingen sajt: mejladressen går före telefonen (regel 13).
    assert m.fordela(_kandidat(), None, webbplats_kravs=False) == ("iris", None)


@pytest.mark.parametrize(
    ("kandidat", "vantat"),
    [
        # En HR-adress är ingen säljadress, inte heller utan sajtkrav.
        (_kandidat(_epost="jobb@hagmanstak.se", _telefon=None), ("ej_kvalificerad", "Inget kontaktsätt")),
        # Enskild firma: aldrig Iris (NIX, MFL 19 §).
        (_kandidat(orgnr="800101-1234"), ("ej_kvalificerad", "Enskild firma (NIX-kontroll krävs)")),
        # Ingen adress alls: telefonen ger fortfarande ringlistan.
        (_kandidat(_epost=None), ("ring", None)),
    ],
)
def test_utan_sajtkrav_galler_ovriga_regler(kandidat, vantat):
    assert m.fordela(kandidat, None, webbplats_kravs=False) == vantat


async def test_kompletteringen_lamnar_bolaget_utan_sajt_till_iris(monkeypatch):
    async def _ingen_sajt(k, **_k):
        return None

    async def _som_den_ar(k):
        return k

    monkeypatch.setattr(m, "_webbplats", _ingen_sajt)
    monkeypatch.setattr(katalog, "berika", _som_den_ar)

    listspar: list[dict] = []
    assert await m._komplettera([_kandidat()], 1, lage="iris", puls=None, listspar=listspar) == []
    assert [r["spar"] for r in listspar] == ["ring"]

    listspar = []
    [iris] = await m._komplettera(
        [_kandidat()], 1, lage="iris", puls=None, listspar=listspar, webbplats_kravs=False
    )
    assert (iris["contact_email"], iris["kontakt_kalla"], iris["website"]) == (
        "kontor@hagmanstak.se", "register", None)
    assert listspar == []


# -- Registret som källmaterial ---------------------------------------------------


async def test_registerfakta_ar_bolagsfakta_utan_personer_och_nummer(monkeypatch):
    traffar = [
        {
            "company_name": "Hagmans Tak AB", "orgnr": "556000-0101", "postnr": "41502", "ort": "Göteborg",
            "anstallda": 15, "omsattning": 12_000_000, "bolagsform": "Aktiebolag", "status": None,
            "sni_namn": "Takarbeten", "verksamhet": "Bolaget ska bedriva takläggning och plåtarbeten.",
            "website": None, "telefon": "031-12 34 56", "epost": "kontor@hagmanstak.se",
            "personer": [{"roll": "Verkställande direktör", "namn": "Test Testsson"}],
            "url": "https://www.allabolag.se/5560000101",
        },
        {"company_name": "Annat AB", "orgnr": "556999-9999", "url": "https://www.allabolag.se/5569999999"},
    ]
    sokt: list[str] = []

    async def _sok(term, plats, sida):
        sokt.append(term)
        return traffar

    monkeypatch.setattr(allabolag, "sok_sida", _sok)
    url, fakta = await allabolag.registerfakta("556000-0101")
    assert sokt == ["5560000101"]
    assert url == "https://www.allabolag.se/5560000101"
    assert "Verksamhet: Bolaget ska bedriva takläggning och plåtarbeten." in fakta
    assert "Antal anställda: 15" in fakta
    for privat in ("Test Testsson", "031-12 34 56", "kontor@hagmanstak.se"):
        assert privat not in fakta

    # Bara en träff med samma nummer räknas, och ett ogiltigt nummer söks inte.
    assert await allabolag.registerfakta("556000-0202") is None
    assert await allabolag.registerfakta(None) is None
    assert sokt == ["5560000101", "5560000202"]


# -- Profilen ---------------------------------------------------------------------


def test_kundvalet_bar_kraven_och_andrar_indatahashen():
    assert kundval({}) == {}
    val = kundval({"webbplats_kravs": False, "behov": f"  {BEHOV}  "})
    assert val == {"webbplats_kravs": False, "behov": BEHOV}
    assert indata_hash("", {}, val) != indata_hash("", {}, {})
    assert tom_profil()["webbplats_kravs"] is True and tom_profil()["behov"] == ""


async def test_profilen_far_kraven_och_storleken_ur_icp():
    profil = await kompilera(
        "", {"size": {"anstallda_min": 1, "anstallda_max": 200}}, {"webbplats_kravs": False, "behov": BEHOV}
    )
    assert (profil["anstallda_min"], profil["anstallda_max"]) == (1, 200)
    assert profil["webbplats_kravs"] is False and profil["behov"] == BEHOV
    # Inte samma sak som utan_webbplats (webbyråernas målgrupp, slår på
    # webbmätningen i researchen).
    assert profil["utan_webbplats"] is False
    assert produktmatch_text(profil) == BEHOV
    assert produktmatch_text(tom_profil()) == "Har ett belagt behov av det kunden säljer"


def test_behovskravet_renderas_som_kundtext():
    text = render_profil({**tom_profil(), "behov": BEHOV, "webbplats_kravs": False})
    # Kundskrivet förblir kundskrivet (INV-SEC-009): inuti omslaget.
    # Samma form som kriterierna, med id:t först: modellen svarar med det.
    rad = f"- kp [BEHOVSKRAV, avgör produktmatchningen]: {BEHOV}"
    assert rad in text and "En egen webbplats krävs inte" in text
    start = text.index("kundens Iris-profil")
    assert text.index(rad) > start


def test_bedomningens_kp_rad_heter_som_behovskravet():
    profil = {**tom_profil(), "behov": BEHOV}
    korpus = "Verksamhet: Bolaget ska bedriva takläggning och plåtarbeten."
    fynd = {"bedomningar": [{"kriterie_id": PRODUKTMATCH, "utslag": "ja", "resonemang": "Säljer takarbeten.",
                             "belagg": [{"url": "https://www.allabolag.se/5560000101",
                                         "citat": "Bolaget ska bedriva takläggning och plåtarbeten."}]}]}
    ut = bedom(profil, fynd, korpus=korpus, produkt_vald=True)
    [kp] = [r for r in ut["score_breakdown"] if r["nyckel"] == PRODUKTMATCH]
    assert (kp["etikett"], kp["utfall"]) == (BEHOV, "träff")
    assert ut["niva"] != "C"


# -- Researchen ------------------------------------------------------------------


@pytest.fixture
def _fake_deepseek_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


_FAKTA = (
    "Bolag: Hagmans Tak AB\nOrganisationsnummer: 556000-0101\nAntal anställda: 15\n"
    "Verksamhet: Bolaget ska bedriva takläggning och plåtarbeten."
)


def _llm(svar: dict):
    """Researchens enda anrop, med svaret `svar` ovanpå ett minimalt fynd."""
    anrop: list[dict] = []

    async def create(*, model, response_format, temperature, messages, **kwargs):
        anrop.append({"system": messages[0]["content"],
                      "user": next((x["content"] for x in messages if x["role"] == "user"), "")})
        payload = {"sources_used": ["business_register"], "context_refs": ["context_pack"],
                   "company_summary": "Takläggare i Göteborg.", "likely_pains": [], "evidence": [],
                   "lagesbeskrivning": "Takläggare.", "motivering": "Säljer takarbeten.", **svar}
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()

    klient = type("K", (), {})()
    klient.chat = klient
    klient.completions = klient
    klient.create = create
    return klient, anrop


async def _kor(storage, prospect_id: str, svar: dict):
    from app.agent.leads_research_v2 import run_research_step_v2

    klient, anrop = _llm(svar)
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=klient),
        patch.object(allabolag, "registerfakta", AsyncMock(return_value=("https://www.allabolag.se/5560000101", _FAKTA))),
    ):
        ut = await run_research_step_v2(
            storage, TENANT, prospect_id=prospect_id, tenant_name="Snajp",
            context_pack="## Kontextpaket", brief="", is_test=True,
        )
    return ut, anrop


async def _snajplik(storage, **installningar) -> str:
    await storage.set_agent_settings(
        TENANT, agent_type="leads",
        settings={"produkter": [{"namn": "Iris, leadsagenten", "nytta": "hittar nya företagskunder"},
                                {"namn": "Supportagenten", "nytta": "svarar på kundfrågor"}],
                  **installningar},
    )
    prospekt = await storage.create_prospect(
        TENANT, company_name="Hagmans Tak AB", profil={"orgnr": "556000-0101", "anstallda": 15}
    )
    return prospekt["id"]


async def test_bolaget_utan_sajt_bedoms_mot_behovskravet(_fake_deepseek_key):
    storage = MemoryStorage()
    pid = await _snajplik(storage, webbplats_kravs=False, behov=BEHOV)
    ja = {"bedomningar": [{"kriterie_id": "kp", "utslag": "ja", "resonemang": "Säljer takarbeten.",
                           "belagg": [{"url": "https://www.allabolag.se/5560000101",
                                       "citat": "Bolaget ska bedriva takläggning och plåtarbeten."}]}],
          # Modellen lämnade produkten tom: behovskravet avgör ändå.
          "produkt": None}
    ut, [anrop] = await _kor(storage, pid, ja)

    assert "## Registeruppgifter (källa: https://www.allabolag.se/5560000101)" in anrop["user"]
    assert f"- kp [BEHOVSKRAV, avgör produktmatchningen]: {BEHOV}" in anrop["user"]
    # Behovskravet ERSÄTTER produktfrågan: två frågor om kp gav blandade svar.
    uppgift = anrop["system"] + anrop["user"]
    assert "är kundens BEHOVSKRAV i IRIS-PROFILEN och inget annat" in uppgift
    assert "affärskontexten)? Utslaget är" not in uppgift
    assert "null BARA när källmaterialet visar" not in uppgift
    # Overlayens kp-punkt säger samma sak, så att systemlagret inte drar åt
    # produktfrågan (agent-core/overlays/leads-research-v2.md).
    assert "Står ett BEHOVSKRAV på kp-raden i IRIS-PROFILEN ersätter det frågan" in anrop["system"]
    # Kundens text står aldrig i uppgiften eller systemlagret.
    assert BEHOV not in anrop["system"]

    prospekt = await storage.get_prospect(TENANT, pid)
    assert prospekt["niva"] in ("A", "B"), prospekt.get("motivering")
    assert ut["qualified"] is True


async def test_utslaget_under_kravets_namn_raknas_som_kp(_fake_deepseek_key):
    # Provet i development 2026-10-30 (Hagmans Tak): ja med belägg, men med
    # kriterie_id "BEHOVSKRAV" i stället för "kp".
    storage = MemoryStorage()
    pid = await _snajplik(storage, webbplats_kravs=False, behov=BEHOV)
    svar = {"bedomningar": [{"kriterie_id": "BEHOVSKRAV", "utslag": "ja", "resonemang": "Säljer takarbeten.",
                             "belagg": [{"url": "https://www.allabolag.se/5560000101",
                                         "citat": "Bolaget ska bedriva takläggning och plåtarbeten."}]}],
            "produkt": "Iris, leadsagenten"}
    ut, _ = await _kor(storage, pid, svar)
    prospekt = await storage.get_prospect(TENANT, pid)
    assert prospekt["niva"] in ("A", "B"), prospekt.get("motivering")
    [kp] = [r for r in prospekt["score_breakdown"] if r["nyckel"] == "kp"]
    assert kp["utfall"] == "träff"

    # Utan behovskrav rör koden inte modellens id:n: kp saknas och fäller,
    # och uppgiften ställer produktfrågan som förut.
    storage = MemoryStorage()
    pid = await _snajplik(storage, webbplats_kravs=False)
    _, [anrop] = await _kor(storage, pid, svar)
    assert (await storage.get_prospect(TENANT, pid))["niva"] == "C"
    assert "affärskontexten)? Utslaget är" in anrop["system"] + anrop["user"]
    assert "BEHOVSKRAV, avgör" not in anrop["user"]


async def test_utan_kundval_ar_researchen_som_forut(_fake_deepseek_key):
    storage = MemoryStorage()
    pid = await _snajplik(storage)
    ut, anrop = await _kor(storage, pid, {})
    # Ingen sajt och inget registeruppslag: inget källmaterial, inget anrop.
    assert anrop == []
    prospekt = await storage.get_prospect(TENANT, pid)
    assert prospekt["niva"] == "C"
    assert "Inget källmaterial" in prospekt["motivering"]
