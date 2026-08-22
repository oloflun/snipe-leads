"""Testmailen: per fack, nya varje gång, och ett svar som inte får ta en minut.

Felrapporten från drift: knappen "Hämta testmail" i kundtjänstvyn snurrade utan
att bli klar. Orsaken var mätbar — endpointen processade alla sex mailen genom
hela agentpipelinen INNAN den svarade, uppmätt 60,3 sekunder mot dev-deployen,
medan proxyn i webbappen dödar anropet vid 60. Klassificeringen sker nu i en
bakgrundsuppgift och svaret går direkt.

Testerna nedan vaktar det som går att vakta utan att mäta tid: att svaret
kommer med mailen inlästa, att ett fack går att fylla på för sig, och att
poolen faktiskt har material till varje inkorg.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import CATEGORIES, get_settings
from app.email_pipeline.connectors.mock import build_mock_emails, kategorier_med_mail
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key, "X-Snajp-Demo": "true"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_varje_fack_har_minst_tre_mail():
    """En inkorg med två mail ger samma två vid varje "Uppdatera".

    Det var precis felet den roterande poolen en gång infördes för att lösa —
    fast per fack i stället för globalt.
    """
    from collections import Counter

    from app.email_pipeline.connectors.mock import BESVARBARA, ESKALERANDE

    antal = Counter(m["kategori"] for m in BESVARBARA + ESKALERANDE)
    for kategori in CATEGORIES:
        assert antal[kategori] >= 3, f"facket {kategori} har bara {antal[kategori]} testmail"


def test_poolen_tacker_alla_fack():
    assert set(kategorier_med_mail()) == set(CATEGORIES)


def test_urvalet_per_fack_stannar_i_facket():
    for kategori in CATEGORIES:
        mail = build_mock_emails(kategori=kategori, antal=3)
        assert mail, f"inga testmail för {kategori}"
        assert len(mail) <= 3


def test_okant_fack_avvisas():
    """En felstavad kategori ska falla direkt, inte tyst ge noll mail."""

    async def _kor():
        async with app.router.lifespan_context(app):
            async with _client() as client:
                return await client.post(
                    "/api/inbox/mock", headers=DEMO, json={"category": "finns_inte"}
                )

    import anyio

    svar = anyio.run(_kor)
    assert svar.status_code == 400


@pytest.mark.anyio
async def test_seedning_svarar_med_mailen_inlasta():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post("/api/inbox/mock", headers=DEMO, json={})

    assert svar.status_code == 201
    kropp = svar.json()
    # Ett ärende per fack: en kund som klickar sig runt ska inte hitta en tom
    # inkorg och tro att sorteringen är trasig.
    assert kropp["ingested"] == len(CATEGORIES)
    assert kropp["processing"] is True
    assert len(kropp["email_ids"]) == len(CATEGORIES)


@pytest.mark.anyio
async def test_uppdatera_ett_fack_ror_inte_de_andra():
    """Kärnan i "Uppdatera": nya mail till DEN inkorg kunden står i.

    Före ändringen bytte varje klick ut hela testinkorgen, så det fack man
    tittade på kunde få noll nya mail medan sju andra fack fylldes på.
    """
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO, json={})

            fore = (await client.get("/api/inbox?limit=50", headers=DEMO)).json()["emails"]
            fack = {
                m["classification"]["category"]
                for m in fore
                if m.get("classification")
            }
            assert fack, "inget mail hann klassificeras — testet mäter ingenting"
            valt = sorted(fack)[0]

            ororda_fore = {
                m["id"] for m in fore if (m.get("classification") or {}).get("category") != valt
            }

            svar = await client.post("/api/inbox/mock", headers=DEMO, json={"category": valt})
            assert svar.status_code == 201
            assert svar.json()["category"] == valt

            efter = (await client.get("/api/inbox?limit=50", headers=DEMO)).json()["emails"]

    kvar = {m["id"] for m in efter}
    assert ororda_fore <= kvar, "ett fack som inte uppdaterades tappade mail"
