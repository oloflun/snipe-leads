"""Ett id per anrop, i svaret, i loggen och i felposten (Fas 0-fyndet H12)."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from app import sparning
from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    # raise_app_exceptions=False: 500-svaret ska komma tillbaka som ett svar,
    # som det gör bakom uvicorn, i stället för att kastas in i testet.
    return AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test")


_prov = APIRouter()
_sedda_i_vagen: list[str | None] = []


@_prov.get("/_prov/kasta")
async def _kasta() -> dict:
    _sedda_i_vagen.append(sparning.anrops_id())
    raise RuntimeError("hemlig intern detalj")


app.include_router(_prov)


class _Fangare(logging.Handler):
    """En hanterare med samma filter som den riktiga, så att testet ser vad
    som faktiskt hamnar på loggraden."""

    def __init__(self) -> None:
        super().__init__()
        self.addFilter(sparning._Anropsfilter())
        self.rader: list[tuple[str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.rader.append((record.getMessage(), record.anrop))


async def test_varje_svar_bar_ett_id():
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            a = await klient.get("/health/live")
            b = await klient.get("/health/live")

    assert a.headers["x-request-id"] and b.headers["x-request-id"]
    assert a.headers["x-request-id"] != b.headers["x-request-id"]


async def test_inkommande_id_ateranvands_om_det_ar_ett_id():
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            giltigt = await klient.get("/health/live", headers={"X-Request-Id": "webb-1234567890abcdef"})
            ogiltigt = await klient.get("/health/live", headers={"X-Request-Id": "a b\tc<script>"})

    assert giltigt.headers["x-request-id"] == "webb-1234567890abcdef"
    assert ogiltigt.headers["x-request-id"] != "a b\tc<script>"
    assert sparning._GILTIGT.match(ogiltigt.headers["x-request-id"])


async def test_ett_ohanterat_fel_ger_samma_referens_i_svar_logg_och_handelse():
    fangare = _Fangare()
    logging.getLogger().addHandler(fangare)
    _sedda_i_vagen.clear()
    try:
        async with app.router.lifespan_context(app):
            async with _klient() as klient:
                svar = await klient.get("/_prov/kasta")
            handelser = await app.state.storage.list_platform_events(limit=10)
    finally:
        logging.getLogger().removeHandler(fangare)

    assert svar.status_code == 500
    referens = svar.headers["x-request-id"]
    assert svar.json()["referens"] == referens
    assert "hemlig intern detalj" not in svar.text, "undantagets text får aldrig nå klienten"

    # Vägen själv såg id:t ...
    assert _sedda_i_vagen == [referens]
    # ... felraden i loggen bär det, fast den skrivs utanför mellanlagret ...
    felrader = [anrop for text, anrop in fangare.rader if text.startswith("Ohanterat fel på GET /_prov/kasta")]
    assert felrader == [referens]
    # ... och händelsetabellen bär samma värde.
    fel = [h for h in handelser if (h.get("detail") or {}).get("path") == "/_prov/kasta"]
    assert fel and fel[0]["detail"]["anrop"] == referens


async def test_id_t_lacker_inte_till_nasta_anrop():
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            await klient.get("/_prov/kasta")
            assert sparning.anrops_id() is None, "id:t ska vara återställt efter anropet, även efter ett fel"


def test_filtret_satter_id_inom_ett_anrop_och_streck_utanfor():
    post = logging.LogRecord("x", logging.INFO, __file__, 1, "hej", None, None)
    sparning._Anropsfilter().filter(post)
    assert post.anrop == "-"

    token = sparning._anrop.set("abc12345")
    try:
        sparning._Anropsfilter().filter(post)
        assert post.anrop == "abc12345"
    finally:
        sparning._anrop.reset(token)


def test_json_formatet_ger_en_rad_med_falt():
    post = logging.LogRecord("snajp-support", logging.WARNING, __file__, 1, "Långsamt anrop: %s", ("GET /x",), None)
    post.anrop = "abc12345"
    rad = json.loads(sparning._JsonFormat().format(post))
    assert rad["level"] == "warning"
    assert rad["message"] == "Långsamt anrop: GET /x"
    assert rad["anrop"] == "abc12345"
    assert rad["logger"] == "snajp-support"
