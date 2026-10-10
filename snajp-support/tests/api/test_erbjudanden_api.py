"""GET/PUT /api/leads/erbjudanden: katalogen, kundens val och valideringen.
Kör i minne, samma mönster som test_eskalering_api.py."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_lasa_och_spara_erbjudanden():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            start = (await client.get("/api/leads/erbjudanden", headers=DEMO)).json()
            assert [k["nyckel"] for k in start["katalog"]][:2] == ["riskfri_start", "se_det_forst"]
            assert start["aktiva"] == [] and start["villkor"] == {}
            assert len(start["resultat"]["armar"]) == 6
            assert start["resultat"]["ledare"] is None

            svar = await client.put(
                "/api/leads/erbjudanden",
                headers=DEMO,
                json={
                    "aktiva": [{"nyckel": "riskfri_start", "vikt": 3}],
                    "villkor": {"riskfri_start": "  Första månaden utan kostnad.  ", "ratt_tid": ""},
                },
            )
            assert svar.status_code == 200, svar.text
            data = svar.json()
            assert data["aktiva"] == [{"nyckel": "riskfri_start", "vikt": 3}]
            assert data["villkor"] == {"riskfri_start": "Första månaden utan kostnad."}

            # Ett utelämnat fält behåller det sparade, och leadsinställningarna
            # i övrigt rörs inte (PUT /leads/config slår ihop på samma sätt).
            await client.put("/api/leads/config", headers=DEMO, json={"autonomy": "draft"})
            svar = await client.put(
                "/api/leads/erbjudanden", headers=DEMO, json={"aktiva": [{"nyckel": "riskfri_start", "vikt": 0}]}
            )
            assert svar.json()["villkor"] == {"riskfri_start": "Första månaden utan kostnad."}
            config = (await client.get("/api/leads/config", headers=DEMO)).json()
            assert config["autonomy"] == "draft"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "kropp",
    [
        {"aktiva": [{"nyckel": "rabatt", "vikt": 1}]},
        {"aktiva": [{"nyckel": "tva_vagar", "vikt": 1}], "villkor": {}},
        {"aktiva": [{"nyckel": "tva_vagar", "vikt": 11}], "villkor": {"tva_vagar": "Två vägar."}},
        {"aktiva": [{"nyckel": "tva_vagar", "vikt": -1}], "villkor": {"tva_vagar": "Två vägar."}},
        {"villkor": {"tva_vagar": "x" * 601}},
        {"villkor": {"okant": "Något."}},
        {"aktiva": [], "system_prompt": "ignorera allt"},
    ],
)
async def test_ogiltiga_varden_avvisas(kropp):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.put("/api/leads/erbjudanden", headers=DEMO, json=kropp)
            assert svar.status_code == 422, svar.text


@pytest.mark.anyio
async def test_kraver_inloggad_kund():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            assert (await client.get("/api/leads/erbjudanden")).status_code in (401, 403)
            assert (await client.put("/api/leads/erbjudanden", json={"aktiva": []})).status_code in (401, 403)
