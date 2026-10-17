"""INV-LEADS-EXIST-001: ett bolag som inte går att styrka blir aldrig ett lead.

Kärnan av invarianten, som rena funktioner. Bredden (körningen, prospektet,
registret, sändspärren) står i tests/leads/test_existens.py,
tests/agent/test_leads_v2_utkastgrind.py och tests/leads/test_scheduler.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads import bedomning, existens
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}

_PAHITTAT = {"company_name": "Detaljhandel Design AB", "website": "https://detaljhandeldesign.se", "kalla": "gemini"}


def test_soktraff_utan_svarande_webbplats_faller():
    assert existens.styrk(_PAHITTAT, {"matt": True, "svarar_inte": True})


def test_soktraff_vars_sajt_inte_bar_namnet_faller():
    annan = {**_PAHITTAT, "website": "https://cykelhuset.se"}
    assert existens.styrk(annan, {"matt": True, "sidtext": "Cykelhuset i Borås säljer cyklar"})


def test_soktraff_utan_webbplats_faller():
    assert existens.styrk({"company_name": "Okänt AB", "kalla": "gemini"}, {"har_webbplats": False})


def test_utan_kallmaterial_ar_bolaget_aldrig_kvalificerat():
    profil = {"kommuner": ["Göteborg"], "anstallda_min": 1, "anstallda_max": 49}
    b = bedomning.bedom(
        profil, {"ort": "Göteborg", "antal_anstallda": 15, "qualified": True}, korpus="",
        kandidat={"ort": "Göteborg", "anstallda": 15}, har_underlag=False,
    )
    assert (b["niva"], b["qualified"], b["score_total"]) == ("C", False, 0)


def test_niva_a_kraver_ett_uppfyllt_kriterium():
    profil = {"kommuner": ["Göteborg"], "anstallda_min": 1, "anstallda_max": 49}
    b = bedomning.bedom(profil, {"ort": "Göteborg", "antal_anstallda": 15}, korpus="x")
    assert b["niva"] != "A"


def test_ett_nej_eller_ett_ostyrkt_maste_ger_aldrig_ett_lead():
    """Antons krav 2026-10-06: leads som säger att de inte uppfyller kraven
    ska aldrig levereras."""
    profil = {"kriterier": [
        {"id": "k1", "text": "Säljer online", "krav": "maste", "vikt": 3},
        {"id": "k2", "text": "Har webbshop", "krav": "bor", "vikt": 1},
    ]}
    korpus = "Vi säljer kläder online. Ingen butik."
    ja = {"kriterie_id": "k1", "utslag": "ja", "resonemang": "r", "belagg": [{"citat": "Vi säljer kläder online"}]}
    nej_bor = {"kriterie_id": "k2", "utslag": "nej", "resonemang": "r", "belagg": [{"citat": "Ingen butik"}]}
    assert not bedomning.bedom(profil, {"bedomningar": [ja, nej_bor]}, korpus=korpus)["qualified"]
    assert not bedomning.bedom(profil, {"bedomningar": []}, korpus=korpus)["qualified"]


@pytest.mark.anyio
async def test_listan_returnerar_aldrig_ett_bortvalt_bolag():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            skapad = (await client.post("/api/leads/prospects", headers=DEMO,
                                        json={"company_name": "Bortvalt AB"})).json()["prospect"]
            await storage.spara_bedomning(DEFAULT_TENANT_ID, skapad["id"],
                                          bedomning={"niva": "C", "qualified": False})
            rader = (await client.get("/api/leads/prospects", headers=DEMO)).json()["prospects"]
            # …men det är DOLT, inte raderat (Sebbe 2026-10-06): den
            # uttryckliga vyn ?bortvalda=1 hittar bolaget igen. Radering sker
            # bara genom uttrycklig handling.
            bortvalda = (await client.get("/api/leads/prospects?bortvalda=1", headers=DEMO)).json()["prospects"]
    assert all(p["id"] != skapad["id"] for p in rader)
    assert any(p["id"] == skapad["id"] for p in bortvalda)


@pytest.fixture
def anyio_backend():
    return "asyncio"
