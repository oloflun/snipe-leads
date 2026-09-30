"""Iris-profilen tolkar ALL kundtext och tappar inget tyst (plan 1.3).

Fixturen är Alunix-körningen 2026-09-29, redigerad: orgnr, e-post och namn
är utbytta. Modellsvaret är mockat — det som prövas är vår kod runt det:
validering, sammanslagning med ICP, täckning och rendering.
"""

import pytest

from app.leads import profil as profilmodul
from app.leads.profil import kompilera, render_profil, sakerstall_profil, som_icp, utan_adminrader
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

KUNDTEXT = """Organisationsnummer: 000000-0000
Webbplats: https://exempelbyra.se/
Bransch: Marknadsföring & media
Vad vi säljer: Hemsidor och digital marknadsföring åt företag.
Särskilt fokus: Hitta företag i Göteborg och Mölndal, börja i Sisjön och arbeta dig utåt mot resten av staden.
Fokusera på företag med gamla, dåligt optimerade hemsidor eller ingen sida alls.
Kontaktperson: Exempel Person (VD) — person@example.se
Faktureringsadress: Gatan 1, 111 11 Stad"""

MODELLSVAR = {
    "egen_bransch": "Marknadsföring & media",
    "erbjudande": "Hemsidor och digital marknadsföring åt företag",
    "malgrupp": "Småföretag i Göteborg och Mölndal med gammal eller ingen hemsida",
    "branscher": [],
    "undvik_branscher": [],
    "kommuner": ["Göteborg", "Mölndal"],
    "geo_prioritet": [
        {"etikett": "Sisjön", "postnr_prefix": ["421"]},
        {"etikett": "Övriga Göteborg", "postnr_prefix": ["400", "411", "412", "413", "414", "415", "416", "417", "418"]},
        {"etikett": "Mölndal", "postnr_prefix": ["431"]},
    ],
    "anstallda_min": None,
    "anstallda_max": None,
    "utan_webbplats": True,
    "kriterier": [
        {
            "text": "Har en gammal, dåligt optimerad hemsida eller ingen hemsida alls",
            "krav": "maste",
            "vikt": 3,
            "belagg": "webbsignal",
            "kallmening": "Fokusera på företag med gamla, dåligt optimerade hemsidor eller ingen sida alls.",
        }
    ],
    "uteslut": [],
    "roller": [],
    "vinklar": [{"kriterie_id": "k1", "vinkel": "Er sajt är inte mobilanpassad — vi bygger en som är det."}],
    "ej_tolkat": ["Webbplats: https://exempelbyra.se/"],
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def modell(monkeypatch):
    anrop: list[str] = []

    async def _svar(kundtext, icp):
        anrop.append(kundtext)
        return MODELLSVAR

    monkeypatch.setattr(profilmodul, "_anropa_modell", _svar)
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield anrop
    get_settings.cache_clear()


def test_adminrader_nar_aldrig_prompten():
    ren = utan_adminrader(KUNDTEXT)
    assert "Organisationsnummer" not in ren
    assert "Faktureringsadress" not in ren
    assert "person@example.se" not in ren
    assert "Särskilt fokus" in ren


async def test_alunixprofilen_tolkas_och_inget_tappas(modell):
    p = await kompilera(KUNDTEXT, {"size": {"anstallda_min": 1, "anstallda_max": 49}, "roles": ["VD"]})
    assert p["kalla"] == "ai"
    # Adminraderna skickades aldrig till modellen.
    assert "000000-0000" not in modell[0]
    assert p["kommuner"] == ["Göteborg", "Mölndal"]
    assert p["geo_prioritet"][0]["etikett"] == "Sisjön"
    assert p["utan_webbplats"] is True
    assert p["kriterier"][0]["krav"] == "maste"
    # Strukturerat vinner: storleken från ICP:n, inte från tolkningen.
    assert (p["anstallda_min"], p["anstallda_max"]) == (1, 49)
    # Egen bransch är aldrig ett målfilter.
    assert p["branscher"] == []
    assert p["egen_bransch"] == "Marknadsföring & media"
    # Täckningen: alla målgruppsmeningar är redovisade.
    assert p["otolkat"] == [], p["otolkat"]
    text = render_profil(p)
    assert "EGEN bransch" in text and "ALLA" in text and "Sisjön" in text


async def test_effektiv_icp_far_kommunerna_ur_fritexten(modell):
    p = await kompilera(KUNDTEXT, {})
    icp = som_icp(p, {})
    assert icp["geography"] == ["Göteborg", "Mölndal"]


async def test_modellfel_ger_arlig_regelprofil(monkeypatch):
    async def _fel(*_a, **_k):
        raise TimeoutError

    monkeypatch.setattr(profilmodul, "_anropa_modell", _fel)
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    p = await kompilera(KUNDTEXT, {"industries": ["Bygg"]})
    get_settings.cache_clear()
    assert p["kalla"] == "regler"
    assert p["branscher"] == ["Bygg"]
    assert any("Sisjön" in m for m in p["ej_tolkat"])
    assert "misslyckades" in p["anmarkning"]


async def test_profilen_sparas_och_kompileras_om_bara_vid_ny_indata(modell):
    storage = MemoryStorage()
    await storage.save_context_doc("t1", kind="product_marketing", content=KUNDTEXT, source="test")
    forsta = await sakerstall_profil(storage, "t1")
    andra = await sakerstall_profil(storage, "t1")
    assert forsta["version"] == andra["version"]
    assert len(modell) == 1
    installningar = await storage.get_agent_settings("t1", agent_type="leads")
    await storage.set_agent_settings(
        "t1", agent_type="leads", settings={**installningar, "icp": {"industries": ["Bygg"]}}
    )
    tredje = await sakerstall_profil(storage, "t1")
    assert len(modell) == 2
    assert tredje["branscher"] == ["Bygg"]


async def test_profilendpointen_svarar_utan_nyckel():
    from httpx import ASGITransport, AsyncClient

    from app.config import get_settings
    from app.main import app

    demo = {"X-API-Key": get_settings().snajp_demo_api_key}
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.get("/api/leads/profil", headers=demo)
    assert svar.status_code == 200, svar.text
    assert svar.json()["profil"]["kalla"] == "regler"


def test_lan_som_omrade_forsvinner_inte():
    from app.leads.profil import slå_ihop, tom_profil

    p = slå_ihop(tom_profil(), {"geography": ["Västra Götaland", "Mölndal"]})
    assert p["kommuner"] == ["Mölndal"]
    assert p["omraden"] == ["Västra Götaland"]
    assert "Västra Götaland" in render_profil(p)
