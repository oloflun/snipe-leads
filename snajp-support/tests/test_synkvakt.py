"""Synkvakten (app/jobs/synkvakt.py) och spegelns synkfält (runbookens steg 11).

Prövar: åldern i minuter och gränsen 60, att larmet bara loggas i
development och högst en gång i timmen, att databasen tittas på högst var
femte minut, att ett fel aldrig når loopen, att loggraden bara bär ålder och
utfall, och att PostgresStorage.spegel_info läser synkens kolumner bara när
de finns.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.jobs import synkvakt

NU = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _rent():
    synkvakt.nollstall()
    yield
    synkvakt.nollstall()


class _Lagring:
    def __init__(self, spegel=None, fel: Exception | None = None):
        self.spegel = spegel
        self.fel = fel
        self.anrop = 0

    async def spegel_info(self):
        self.anrop += 1
        if self.fel:
            raise self.fel
        return self.spegel


class _Klocka:
    def __init__(self):
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def _spegel(minuter: int | None, *, miljo: str = "development", utfall: str = "avbruten: x") -> dict:
    return {
        "environment": miljo,
        "seeded_at": None,
        "lage": "envags",
        "synkad_at": None if minuter is None else (NU - timedelta(minutes=minuter)).isoformat(),
        "senaste_forsok_at": NU.isoformat(),
        "senaste_utfall": utfall,
        "senaste_antal": {},
    }


# -- Åldern och gränsen --------------------------------------------------------


def test_alder_i_hela_minuter_och_okand_utan_synk():
    assert synkvakt.synk_alder_min(None, nu=NU) is None
    assert synkvakt.synk_alder_min({"environment": "development"}, nu=NU) is None
    assert synkvakt.synk_alder_min(_spegel(None), nu=NU) is None
    assert synkvakt.synk_alder_min({"synkad_at": "inte en tid"}, nu=NU) is None
    assert synkvakt.synk_alder_min(_spegel(61), nu=NU) == 61
    # datetime direkt, och en naiv tid räknas som UTC.
    assert synkvakt.synk_alder_min({"synkad_at": NU - timedelta(seconds=150)}, nu=NU) == 2
    assert synkvakt.synk_alder_min({"synkad_at": (NU - timedelta(minutes=5)).replace(tzinfo=None)}, nu=NU) == 5
    # En klocka som går före ger aldrig negativ ålder.
    assert synkvakt.synk_alder_min({"synkad_at": NU + timedelta(minutes=3)}, nu=NU) == 0


def test_forsenad_bara_over_sextio_minuter():
    assert synkvakt.synk_forsenad(None) is False
    assert synkvakt.synk_forsenad(60) is False
    assert synkvakt.synk_forsenad(61) is True


# -- Larmet ---------------------------------------------------------------------


@pytest.mark.anyio
async def test_larmar_en_gang_i_timmen(caplog):
    lagring, klocka = _Lagring(_spegel(90)), _Klocka()
    with caplog.at_level(logging.ERROR, logger="snajp-support.synkvakt"):
        assert await synkvakt.vakta(lagring, klocka=klocka, nu=NU) is True
        # Kontrollen tittar högst var femte minut.
        klocka.t += 60
        assert await synkvakt.vakta(lagring, klocka=klocka, nu=NU) is False
        assert lagring.anrop == 1
        # Fortfarande försenad efter fem minuter: tittar, men larmar inte igen.
        klocka.t += synkvakt.KONTROLL_SEKUNDER
        assert await synkvakt.vakta(lagring, klocka=klocka, nu=NU) is False
        assert lagring.anrop == 2
        # En timme efter förra larmet: nytt larm.
        klocka.t = 1000.0 + synkvakt.LARM_SEKUNDER
        assert await synkvakt.vakta(lagring, klocka=klocka, nu=NU) is True
    fel = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(fel) == 2
    rad = fel[0].getMessage()
    assert "90 min" in rad and "avbruten: x" in rad


@pytest.mark.anyio
async def test_larmar_inte_nar_synken_ar_farsk_eller_okand(caplog):
    utan_utfall = _spegel(None)
    utan_utfall["senaste_utfall"] = None
    with caplog.at_level(logging.ERROR, logger="snajp-support.synkvakt"):
        for spegel in (_spegel(60, utfall="ok"), _spegel(5, utfall="hoppade:0"), utan_utfall, None):
            synkvakt.nollstall()
            assert await synkvakt.vakta(_Lagring(spegel), klocka=_Klocka(), nu=NU) is False
    assert not [r for r in caplog.records if r.levelno == logging.ERROR]


def test_avvikande_utfall():
    assert synkvakt.synk_avvikande_utfall(None) is None
    assert synkvakt.synk_avvikande_utfall({"senaste_utfall": None}) is None
    assert synkvakt.synk_avvikande_utfall({"senaste_utfall": "ok"}) is None
    assert synkvakt.synk_avvikande_utfall({"senaste_utfall": "hoppade:0"}) is None
    assert synkvakt.synk_avvikande_utfall({"senaste_utfall": "hoppade:12"}) == "hoppade:12"
    assert synkvakt.synk_avvikande_utfall({"senaste_utfall": "fel: OperationalError"}) == "fel: OperationalError"
    assert synkvakt.synk_avvikande_utfall({"senaste_utfall": "avbruten: x"}) == "avbruten: x"


@pytest.mark.anyio
async def test_upprepade_partiella_fel_larmar_trots_farsk_synk(caplog):
    """Codex runda 9: synken sätter synkad_at även när rader hoppas över, så
    en färsk tid och hoppade:N i varje körning höll vakten tyst för alltid."""
    lagring, klocka = _Lagring(_spegel(3, utfall="hoppade:12")), _Klocka()
    with caplog.at_level(logging.ERROR, logger="snajp-support.synkvakt"):
        assert await synkvakt.vakta(lagring, klocka=klocka, nu=NU) is True
        # Nästa körning hoppar över samma rader, tiden är fortfarande färsk:
        # inget nytt larm inom timmen, men ett nytt efter den.
        klocka.t += synkvakt.KONTROLL_SEKUNDER
        assert await synkvakt.vakta(lagring, klocka=klocka, nu=NU) is False
        klocka.t = 1000.0 + synkvakt.LARM_SEKUNDER
        assert await synkvakt.vakta(lagring, klocka=klocka, nu=NU) is True
        # När raderna rättats och synken lyckas tystnar vakten.
        lagring.spegel = _spegel(3, utfall="ok")
        klocka.t += synkvakt.LARM_SEKUNDER
        assert await synkvakt.vakta(lagring, klocka=klocka, nu=NU) is False
    fel = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert len(fel) == 2
    assert "hoppade:12" in fel[0] and "3 min" in fel[0]


@pytest.mark.anyio
async def test_larmar_bara_i_development(caplog):
    with caplog.at_level(logging.ERROR, logger="snajp-support.synkvakt"):
        assert await synkvakt.vakta(_Lagring(_spegel(500, miljo="main")), klocka=_Klocka(), nu=NU) is False
    assert not [r for r in caplog.records if r.levelno == logging.ERROR]


@pytest.mark.anyio
async def test_ett_fel_nar_aldrig_loopen(caplog):
    with caplog.at_level(logging.WARNING, logger="snajp-support.synkvakt"):
        assert await synkvakt.vakta(_Lagring(fel=RuntimeError("anslutningen föll")), klocka=_Klocka(), nu=NU) is False
    assert any(r.levelno == logging.WARNING for r in caplog.records)


@pytest.mark.anyio
async def test_loggraden_bar_bara_alder_och_utfall(caplog):
    """Inget ur spegeln utöver ålder och utfall når loggen (antal per tabell,
    tider), och ett långt utfall kortas."""
    spegel = _spegel(120, utfall="fel: OperationalError " + "x" * 600)
    spegel["senaste_antal"] = {"ss_emails": {"till_dev": 7}}
    with caplog.at_level(logging.ERROR, logger="snajp-support.synkvakt"):
        await synkvakt.vakta(_Lagring(spegel), klocka=_Klocka(), nu=NU)
    rad = next(r for r in caplog.records if r.levelno == logging.ERROR).getMessage()
    assert "ss_emails" not in rad and "till_dev" not in rad
    assert "x" * 201 not in rad


@pytest.mark.anyio
async def test_stadaren_kor_vakten_aven_nar_stadningen_faller(monkeypatch):
    """Kroken i leads-städarens loop: ett fel i städningen tystar inte vakten."""
    import asyncio
    from types import SimpleNamespace

    from app.jobs import stadare

    anrop: list[object] = []

    async def trasig(_state):
        raise RuntimeError("städningen föll")

    async def vakta(storage):
        anrop.append(storage)
        raise asyncio.CancelledError  # avsluta loopen efter första varvet

    monkeypatch.setattr(stadare, "stada_alla", trasig)
    monkeypatch.setattr(synkvakt, "vakta", vakta)
    monkeypatch.setattr(stadare, "get_settings", lambda: SimpleNamespace(leads_stadning_sekunder=300))
    lagring = object()
    with pytest.raises(asyncio.CancelledError):
        await stadare.run_leads_stadare(SimpleNamespace(storage=lagring))
    assert anrop == [lagring]


# -- PostgresStorage.spegel_info ------------------------------------------------


def _postgres(kolumner: list[str], rad: dict | None):
    from app.storage.postgres import PostgresStorage

    fragor: list[str] = []

    class Conn:
        async def fetchval(self, q, *a):
            fragor.append(q)
            return True

        async def fetch(self, q, *a):
            fragor.append(q)
            return [{"column_name": k} for k in kolumner]

        async def fetchrow(self, q, *a):
            fragor.append(q)
            return rad

    class Acquire:
        async def __aenter__(self):
            return Conn()

        async def __aexit__(self, *a):
            return False

    class Pool:
        def acquire(self):
            return Acquire()

    storage = PostgresStorage.__new__(PostgresStorage)
    storage.pool = Pool()
    return storage, fragor


@pytest.mark.anyio
async def test_spegel_info_i_en_aldre_spegel_utan_synkkolumner():
    storage, fragor = _postgres(["environment", "seeded_at"], {"environment": "development", "seeded_at": NU})
    svar = await storage.spegel_info()
    assert svar == {"environment": "development", "seeded_at": NU.isoformat()}
    assert fragor[-1].startswith("select environment, seeded_at from public.mirror_meta")


@pytest.mark.anyio
async def test_spegel_info_med_synkens_kolumner():
    alla = ["environment", "seeded_at", "lage", "synkad_at", "senaste_forsok_at", "senaste_utfall", "senaste_antal"]
    rad = {
        "environment": "development", "seeded_at": NU, "lage": "envags", "synkad_at": NU,
        "senaste_forsok_at": NU, "senaste_utfall": "hoppade:2",
        "senaste_antal": '{"ss_emails": {"till_dev": 3}}',
    }
    storage, fragor = _postgres(alla, rad)
    svar = await storage.spegel_info()
    assert ("select environment, seeded_at, lage, synkad_at, senaste_forsok_at, senaste_utfall, "
            "senaste_antal from public.mirror_meta") in fragor[-1]
    assert svar["senaste_forsok_at"] == NU.isoformat() and svar["senaste_utfall"] == "hoppade:2"
    assert svar["senaste_antal"] == {"ss_emails": {"till_dev": 3}}


@pytest.mark.anyio
async def test_spegel_info_med_bara_lage_och_trasig_jsonb():
    """Synken har gått men inte hunnit skriva utfallet (kolumnerna skapas
    separat), och en jsonb som inte går att läsa blir None i stället för ett fel."""
    storage, fragor = _postgres(
        ["environment", "seeded_at", "lage", "synkad_at"],
        {"environment": "development", "seeded_at": None, "lage": "envags", "synkad_at": None},
    )
    svar = await storage.spegel_info()
    assert "senaste_utfall" not in fragor[-1] and "senaste_utfall" not in svar
    storage, _ = _postgres(["environment", "seeded_at", "senaste_antal"],
                           {"environment": "development", "seeded_at": None, "senaste_antal": "{trasig"})
    assert (await storage.spegel_info())["senaste_antal"] is None


@pytest.mark.anyio
async def test_spegel_info_utan_markor():
    from app.storage.postgres import PostgresStorage

    class Conn:
        async def fetchval(self, q, *a):
            return False

    class Acquire:
        async def __aenter__(self):
            return Conn()

        async def __aexit__(self, *a):
            return False

    class Pool:
        def acquire(self):
            return Acquire()

    storage = PostgresStorage.__new__(PostgresStorage)
    storage.pool = Pool()
    assert await storage.spegel_info() is None
