"""Kvittoskanningen som jobb med förlopp (fas 2, 2026-11-10).

Skanningen läser inkorgen och gör ett modellanrop per kvittomejl, i en enda
begäran. Webbens proxy ger en POST nio sekunder: en skanning av tjugo mejl
visade ett fel i vyn medan arbetet gick vidare på servern, utan förlopp och
utan utfall efter en omladdning. Nu startar begäran ett jobb och svarar
direkt; vyn hämtar förloppet (mejl x av y) och till sist samma svar som förut.
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.kvitton as kvitton_api
from app.config import DEFAULT_TENANT_ID, get_settings
from app.kvitton.mejl import FEJKMEJL, MejlkontofelError, MockMejlkonto
from app.kvitton.skanning import Skanningsresultat, skanna_inkorg
from app.main import app
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _mock_inkorg(monkeypatch):
    for namn, varde in {
        "KVITTO_MEJL_LEVERANTOR": "mock", "KVITTO_MEJL_TENANT": "", "KVITTO_TOLKNING": "deterministisk",
        "DATABASE_URL": "", "REDIS_URL": "", "GEMINI_API_KEY": "", "OPENAI_API_KEY": "",
    }.items():
        monkeypatch.setenv(namn, varde)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _nyckel() -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_demo_api_key}


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _vanta(klient: AsyncClient, job_id: str) -> dict:
    for _ in range(200):
        svar = (await klient.get(f"/api/kvitton/skanning/{job_id}", headers=_nyckel())).json()
        if svar["status"] in ("completed", "failed"):
            return svar
        await asyncio.sleep(0.02)
    raise AssertionError("skanningen blev aldrig klar")


async def test_skanningen_meddelar_forloppet_mejl_for_mejl():
    sedda: list[tuple[int, int]] = []

    async def _forlopp(lasta: int, totalt: int) -> None:
        sedda.append((lasta, totalt))

    await skanna_inkorg(MemoryStorage(), "t1", MockMejlkonto(), forlopp=_forlopp)

    assert sedda == [(i, len(FEJKMEJL)) for i in range(len(FEJKMEJL) + 1)]


async def test_starten_svarar_direkt_och_jobbet_ger_samma_svar_som_forut():
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            start = await klient.post("/api/kvitton/skanning", headers=_nyckel())
            assert start.status_code == 202, start.text
            klart = await _vanta(klient, start.json()["job_id"])

    assert klart["status"] == "completed"
    resultat = klart["result"]
    assert resultat["genomlasta"] == len(FEJKMEJL)
    assert resultat["handelser"] and resultat["kvitton"] and "sammanfattning" in resultat
    assert klart["forlopp"] == {"lasta": len(FEJKMEJL), "totalt": len(FEJKMEJL)}


async def test_forloppet_syns_medan_skanningen_gar(monkeypatch):
    slapp = asyncio.Event()

    async def _langsam(storage, tenant_id, konto, *, forlopp=None, **_k):
        await forlopp(0, 4)
        await forlopp(2, 4)
        await slapp.wait()
        return Skanningsresultat()

    monkeypatch.setattr(kvitton_api, "skanna_inkorg", _langsam)
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            job_id = (await klient.post("/api/kvitton/skanning", headers=_nyckel())).json()["job_id"]
            await asyncio.sleep(0.05)
            mitt_i = (await klient.get(f"/api/kvitton/skanning/{job_id}", headers=_nyckel())).json()
            slapp.set()
            await _vanta(klient, job_id)

    assert mitt_i["status"] == "processing"
    assert mitt_i["forlopp"] == {"lasta": 2, "totalt": 4}
    assert mitt_i.get("result") is None


async def test_en_andra_start_medan_skanningen_gar_ger_samma_jobb(monkeypatch):
    slapp = asyncio.Event()
    anrop: list[int] = []

    async def _langsam(storage, tenant_id, konto, *, forlopp=None, **_k):
        anrop.append(1)
        await slapp.wait()
        return Skanningsresultat()

    monkeypatch.setattr(kvitton_api, "skanna_inkorg", _langsam)
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            forsta = (await klient.post("/api/kvitton/skanning", headers=_nyckel())).json()
            await asyncio.sleep(0.02)
            andra = (await klient.post("/api/kvitton/skanning", headers=_nyckel())).json()
            slapp.set()
            await _vanta(klient, forsta["job_id"])
            tredje = (await klient.post("/api/kvitton/skanning", headers=_nyckel())).json()
            await _vanta(klient, tredje["job_id"])

    assert andra["job_id"] == forsta["job_id"] and andra.get("pagar") is True
    assert tredje["job_id"] != forsta["job_id"], "en ny skanning efter den första ska starta på riktigt"
    assert len(anrop) == 2


async def test_ett_fel_blir_ett_besked_pa_jobbet(monkeypatch):
    async def _trasig(storage, tenant_id, konto, **_k):
        raise MejlkontofelError("Inloggningen till brevlådan har gått ut. Koppla om den under Inställningar.")

    monkeypatch.setattr(kvitton_api, "skanna_inkorg", _trasig)
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            job_id = (await klient.post("/api/kvitton/skanning", headers=_nyckel())).json()["job_id"]
            klart = await _vanta(klient, job_id)

    assert klart["status"] == "failed"
    assert "brevlådan" in klart["error"]


async def test_ett_ovantat_fel_visar_ingen_intern_text(monkeypatch):
    async def _trasig(storage, tenant_id, konto, **_k):
        raise RuntimeError("psycopg: relation bk_underlag does not exist")

    monkeypatch.setattr(kvitton_api, "skanna_inkorg", _trasig)
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            job_id = (await klient.post("/api/kvitton/skanning", headers=_nyckel())).json()["job_id"]
            klart = await _vanta(klient, job_id)

    assert klart["status"] == "failed"
    assert "psycopg" not in klart["error"] and klart["error"]


async def test_en_annan_kunds_skanning_finns_inte():
    async with app.router.lifespan_context(app):
        frammande = await app.state.jobs.create(tenant_id="00000000-0000-4000-a000-0000000000ff")
        async with _klient() as klient:
            svar = await klient.get(f"/api/kvitton/skanning/{frammande}", headers=_nyckel())
            saknas = await klient.get("/api/kvitton/skanning/finns-inte", headers=_nyckel())

    assert svar.status_code == 404 and saknas.status_code == 404
    assert DEFAULT_TENANT_ID  # jobbet ovan tillhör en annan kund än demonyckelns
