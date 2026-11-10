"""Kaostest: ett beroende som är nere medan api:t går (fas 4, 2026-11-10).

Uppstarten vägrar minnesläge sedan fas 1. Det som återstod var driften: ett
Redis eller en databas som tappar anslutningen efter uppstart gav ett allmänt
serverfel ("Något gick fel på vår sida"), samma svar som ett programfel.
Statuskoden 500 säger till proxyn och till den som felsöker att koden är
trasig; 503 säger att tjänsten är tillfälligt otillgänglig, och det är det som
är sant.
"""

from __future__ import annotations

import asyncio
import errno

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    # raise_app_exceptions=False: felet ska gå genom appens egen felhanterare,
    # som det gör i drift, inte kastas ut i testet.
    return AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test")


def _redisfel() -> Exception:
    import redis.exceptions

    return redis.exceptions.ConnectionError("Error 111 connecting to redis:6379. Connection refused.")


@pytest.mark.parametrize(
    "fel",
    [
        _redisfel(),
        ConnectionRefusedError("[Errno 111] Connection refused"),
        asyncio.TimeoutError(),
        OSError(errno.ENETUNREACH, "Network is unreachable"),
    ],
    ids=["redis", "anslutning-nekad", "tidsgrans", "natet-nere"],
)
async def test_chattstart_med_jobblagret_nere_ger_503_inte_500(monkeypatch, fel):
    async with app.router.lifespan_context(app):
        async def _nere(*_a, **_k):
            raise fel

        monkeypatch.setattr(app.state.jobs, "create", _nere)
        async with _klient() as klient:
            svar = await klient.post("/api/chat", headers=DEMO, json={"message": "Hej, vad kostar frakten?"})

    assert svar.status_code == 503, svar.text
    kropp = svar.json()
    assert "tillfälligt" in kropp["error"]
    assert kropp.get("referens"), "felet ska gå att hitta i loggen"
    for internt in ("redis", "6379", "Errno", "Traceback", "Connection refused"):
        assert internt not in svar.text


async def test_databasen_nere_under_en_lasning_ger_503(monkeypatch):
    import asyncpg

    async with app.router.lifespan_context(app):
        async def _nere(*_a, **_k):
            raise asyncpg.exceptions.ConnectionDoesNotExistError("connection was closed in the middle of operation")

        monkeypatch.setattr(app.state.storage, "list_kb", _nere)
        async with _klient() as klient:
            svar = await klient.get("/api/kb", headers=DEMO)

    assert svar.status_code == 503, svar.text
    assert "asyncpg" not in svar.text and "connection was closed" not in svar.text


async def test_ett_programfel_ar_fortfarande_500(monkeypatch):
    async with app.router.lifespan_context(app):
        async def _trasig(*_a, **_k):
            raise KeyError("saknad_nyckel")

        monkeypatch.setattr(app.state.storage, "list_kb", _trasig)
        async with _klient() as klient:
            svar = await klient.get("/api/kb", headers=DEMO)

    assert svar.status_code == 500
    assert "saknad_nyckel" not in svar.text and svar.json().get("referens")


async def test_halsokontrollen_svarar_medan_jobblagret_ar_nere(monkeypatch):
    """Livskontrollen ska inte hänga på ett beroende: Railway startar annars
    om en process som bara väntar på Redis."""
    async with app.router.lifespan_context(app):
        async def _nere(*_a, **_k):
            raise _redisfel()

        monkeypatch.setattr(app.state.jobs, "create", _nere)
        async with _klient() as klient:
            svar = await asyncio.wait_for(klient.get("/health"), timeout=5)

    assert svar.status_code == 200
