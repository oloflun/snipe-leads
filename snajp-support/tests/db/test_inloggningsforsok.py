"""Spärren mot upprepade inloggningsförsök (migration 125) mot en riktig Postgres.

Prövar det som bara databasen kan visa: att tröskeln spärrar, att väntetiden
stiger för varje ny spärr (1, 5, 15, 60 minuter), att fönstret börjar om, att en
lyckad inloggning nollställer, och att webbens roll når spärren BARA genom
funktionerna: snajp_web och snajp_app kan varken läsa eller skriva tabellen.

Körs i CI-jobbet `databas` (.github/workflows/verify.yml). Vägrar allt annat än
en lokal databas utan spegelmarkör. Nycklarna är syntetiska.
"""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
APP_DSN = os.environ.get("GALLRING_TEST_APP_DSN", "")
WEB_DSN = os.environ.get("GALLRING_TEST_WEB_DSN", "")

pytestmark = pytest.mark.skipif(
    not (DSN and APP_DSN and WEB_DSN),
    reason="Kräver GALLRING_TEST_DSN, GALLRING_TEST_APP_DSN och GALLRING_TEST_WEB_DSN mot en tom testdatabas.",
)

_LOKALA = {"localhost", "127.0.0.1", "::1"}
REG = "select public.inloggningsforsok_registrera($1, $2, $3)"
SPARRAD = "select public.inloggningsforsok_sparrad($1::text[])"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _anslut(dsn: str) -> asyncpg.Connection:
    assert urlsplit(dsn).hostname in _LOKALA, "Testet körs bara mot en lokal databas."
    conn = await asyncpg.connect(dsn)
    assert not await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    return conn


def _nyckel() -> str:
    return f"inloggning:epost:test-{uuid.uuid4().hex}"


async def _minuter_kvar(conn, nyckel: str) -> float:
    return await conn.fetchval(
        "select extract(epoch from sparrad_till - now()) / 60 from public.inloggningsforsok where nyckel = $1",
        nyckel,
    )


async def _lat_sparren_ga_ut(agare, nyckel: str) -> None:
    await agare.execute(
        "update public.inloggningsforsok set sparrad_till = now() - interval '1 second' where nyckel = $1",
        nyckel,
    )


@pytest.mark.anyio
async def test_troskeln_spärrar_och_vantetiden_stiger():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    n = _nyckel()
    try:
        vantan = []
        for _ in range(4):
            # Fyra misslyckade försök: ingen spärr. Det femte spärrar.
            for _ in range(4):
                assert await web.fetchval(REG, n, 5, 900) is None
            assert await web.fetchval(REG, n, 5, 900) is not None
            assert await web.fetchval(SPARRAD, [n, "inloggning:ip:annan"]) is not None
            vantan.append(round(await _minuter_kvar(agare, n)))
            await _lat_sparren_ga_ut(agare, n)
            assert await web.fetchval(SPARRAD, [n]) is None
        assert vantan == [1, 5, 15, 60]
        # Taket: nästa spärr är också 60 minuter.
        for _ in range(5):
            await web.fetchval(REG, n, 5, 900)
        assert round(await _minuter_kvar(agare, n)) == 60
    finally:
        await agare.execute("delete from public.inloggningsforsok where nyckel = $1", n)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_fonstret_borjar_om_och_ett_dygn_nollstaller_nivan():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    n = _nyckel()
    try:
        for _ in range(4):
            await web.fetchval(REG, n, 5, 900)
        # Fönstret (15 min) har gått: räkningen börjar om, ingen spärr.
        await agare.execute(
            "update public.inloggningsforsok set fonster_borjan = now() - interval '16 minutes' where nyckel = $1",
            n,
        )
        assert await web.fetchval(REG, n, 5, 900) is None
        assert await agare.fetchval("select forsok from public.inloggningsforsok where nyckel = $1", n) == 1

        # Hög nivå, men ett dygn utan försök: nästa spärr är åter en minut.
        await agare.execute(
            "update public.inloggningsforsok set sparrniva = 3, forsok = 0, senast = now() - interval '25 hours',"
            " fonster_borjan = now() where nyckel = $1",
            n,
        )
        for _ in range(4):
            await web.fetchval(REG, n, 5, 900)
        assert await web.fetchval(REG, n, 5, 900) is not None
        assert round(await _minuter_kvar(agare, n)) == 1
    finally:
        await agare.execute("delete from public.inloggningsforsok where nyckel = $1", n)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_lyckad_inloggning_nollstaller():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    n = _nyckel()
    try:
        for _ in range(4):
            await web.fetchval(REG, n, 5, 900)
        await web.execute("select public.inloggningsforsok_nollstall($1)", n)
        for _ in range(4):
            assert await web.fetchval(REG, n, 5, 900) is None
    finally:
        await agare.execute("delete from public.inloggningsforsok where nyckel = $1", n)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_approllerna_nar_inte_tabellen():
    web, app = await _anslut(WEB_DSN), await _anslut(APP_DSN)
    try:
        for conn in (web, app):
            for fraga in (
                "select count(*) from public.inloggningsforsok",
                "delete from public.inloggningsforsok",
                "insert into public.inloggningsforsok (nyckel) values ('x')",
            ):
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await conn.execute(fraga)
        # api:t har ingen anledning att röra spärren alls.
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await app.fetchval(REG, _nyckel(), 5, 900)
    finally:
        await web.close()
        await app.close()


@pytest.mark.anyio
async def test_ogiltiga_argument_vagras():
    web = await _anslut(WEB_DSN)
    try:
        with pytest.raises(asyncpg.RaiseError):
            await web.fetchval(REG, "", 5, 900)
        with pytest.raises(asyncpg.RaiseError):
            await web.fetchval(REG, "x" * 201, 5, 900)
        with pytest.raises(asyncpg.RaiseError):
            await web.fetchval(REG, _nyckel(), 0, 900)
    finally:
        await web.close()
