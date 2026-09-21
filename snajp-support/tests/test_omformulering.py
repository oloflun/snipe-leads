"""Omformuleringsknapparna (Förbättra/Kortare/Mer personlig) och den
per-tenant-anpassade mejlsignaturen.

Allt körs i simuleringsläge (conftest tvingar det): omformuleringens
deterministiska transformer och signaturvägen är precis det som ska gå att
falsifiera utan modell.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.email_pipeline.omformulering import omformulera_utkast
from app.email_pipeline.processor import _wrap_reply
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}

_UTKAST = (
    "Hej Anna!\n\n"
    "Tack för din fråga om leveranstider. Standardleveransen tar tre till fem "
    "vardagar. Expressleverans finns för 99 kr och tar en vardag. Du får ett "
    "spårningsnummer via mejl när paketet lämnar lagret. Hör av dig om du "
    "undrar något mer.\n\n"
    "Vänliga hälsningar,\nNordlys Handel"
)

_MEJL = {"from_name": "Anna Lindqvist", "subject": "Leveranstid?", "body_text": "Hur lång är leveranstiden?"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# -- Transformerna (simuleringsläge) ---------------------------------------


@pytest.mark.anyio
async def test_kortare_halverar_men_behaller_ram():
    nytt = await omformulera_utkast(lage="kortare", content=_UTKAST, email=_MEJL)
    assert len(nytt) < len(_UTKAST)
    assert nytt.startswith("Hej Anna!")
    assert nytt.rstrip().endswith("Nordlys Handel")
    # Första sakmeningen ska överleva — det är utfyllnaden som ska bort.
    assert "leverans" in nytt.casefold()


@pytest.mark.anyio
async def test_personligare_anvander_fornamnet():
    utan_namn = _UTKAST.replace("Hej Anna!", "Hej!")
    nytt = await omformulera_utkast(lage="personligare", content=utan_namn, email=_MEJL)
    assert nytt.startswith("Hej Anna!")
    assert "tack för att du hörde av dig" in nytt.casefold()


@pytest.mark.anyio
async def test_forbattra_stadar_utan_att_tappa_innehall():
    stokigt = _UTKAST.replace("Standardleveransen", "Standardleveransen   ").replace(
        "Tack för din fråga", "Tack   för din fråga"
    )
    nytt = await omformulera_utkast(lage="forbattra", content=stokigt, email=_MEJL)
    assert "Tack för din fråga" in nytt
    assert "Standardleveransen " in nytt and "Standardleveransen  " not in nytt
    assert "spårningsnummer" in nytt


@pytest.mark.anyio
async def test_okant_lage_kastar():
    with pytest.raises(ValueError):
        await omformulera_utkast(lage="versaler", content=_UTKAST, email=_MEJL)


# -- API-vägen ---------------------------------------------------------------


@pytest.mark.anyio
async def test_omformulera_endpoint_ror_inte_det_sparade_utkastet():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            pending = next(e for e in emails if e["status"] == "awaiting_approval")
            draft_id = pending["draft"]["id"]
            original = pending["draft"]["content"]

            svar = await client.post(
                f"/api/drafts/{draft_id}/omformulera",
                headers=DEMO,
                json={"lage": "kortare"},
            )
            assert svar.status_code == 200
            assert svar.json()["content"].strip()
            assert svar.json()["lage"] == "kortare"

            # Stateless: det sparade utkastet är oförändrat och fortfarande
            # pending — det som skickas avgörs först vid Godkänn.
            detail = (await client.get(f"/api/inbox/{pending['id']}", headers=DEMO)).json()
            assert detail["draft"]["content"] == original
            assert detail["status"] == "awaiting_approval"

            # Beslutet är spårat.
            assert "draft_omformulerad" in [d["event"] for d in detail["decisions"]]


@pytest.mark.anyio
async def test_omformulera_utgar_fran_granskarens_redigering():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            pending = next(e for e in emails if e["status"] == "awaiting_approval")

            redigerat = (
                "Hej!\n\nFörsta meningen med svaret. Andra meningen med "
                "utfyllnad. Tredje meningen med ännu mer utfyllnad. Fjärde "
                "meningen som avslutar.\n\nVänliga hälsningar,\nNordlys Handel"
            )
            svar = await client.post(
                f"/api/drafts/{pending['draft']['id']}/omformulera",
                headers=DEMO,
                json={"lage": "kortare", "content": redigerat},
            )
            assert svar.status_code == 200
            # Det är GRANSKARENS text som kortats, inte det sparade utkastet.
            assert "Första meningen med svaret." in svar.json()["content"]
            assert "Fjärde meningen" not in svar.json()["content"]


@pytest.mark.anyio
async def test_omformulera_blockeras_pa_hanterat_utkast():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            pending = next(e for e in emails if e["status"] == "awaiting_approval")
            draft_id = pending["draft"]["id"]

            await client.post(f"/api/drafts/{draft_id}/approve", headers=DEMO, json={})
            svar = await client.post(
                f"/api/drafts/{draft_id}/omformulera",
                headers=DEMO,
                json={"lage": "forbattra"},
            )
            assert svar.status_code == 409


@pytest.mark.anyio
async def test_omformulera_validerar_laget():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            pending = next(e for e in emails if e["status"] == "awaiting_approval")

            svar = await client.post(
                f"/api/drafts/{pending['draft']['id']}/omformulera",
                headers=DEMO,
                json={"lage": "versaler"},
            )
            assert svar.status_code == 422


# -- Signaturen --------------------------------------------------------------


def test_wrap_reply_signerar_med_avsandaren():
    resultat = _wrap_reply("Tack för ditt mejl.", "Anna Lindqvist", "Livrustning AB")
    assert resultat.startswith("Hej Anna!")
    assert resultat.endswith("Vänliga hälsningar,\nLivrustning AB")


def test_wrap_reply_dubblerar_inte_avsandarens_signatur():
    resultat = _wrap_reply(
        "Tack!\n\nVänliga hälsningar,\nLivrustning AB", "Anna", "Livrustning AB"
    )
    assert resultat.count("Livrustning AB") == 1


@pytest.mark.anyio
async def test_mejlsvar_signeras_med_tenantens_namn():
    """Nordlys-demon: utkasten ska bära tenantens namn, inte 'Snajp Support' —
    svaret går ut i kundens namn från kundens supportadress."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            await client.post("/api/inbox/mock", headers=DEMO)
            emails = (await client.get("/api/inbox", headers=DEMO)).json()["emails"]
            med_utkast = [e for e in emails if e.get("draft")]
            assert med_utkast
            for e in med_utkast:
                assert "Snajp Support" not in e["draft"]["content"]
                assert "Nordlys Handel" in e["draft"]["content"]
