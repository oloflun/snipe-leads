"""Körningens rapport tål ett tillfälligt fel (Fas 0-fyndet H6, 2026-11-09).

Ett prospektjobb som är klart rapporterar till sin körning: läs tillståndet,
räkna in utfallet, skriv till Redis och till liggaren. Före: ett enda fel i
något av de stegen (en Redis-anslutning som bröts, en tidsgräns) fällde hela
körningen och tappade rapporten, fast researchen redan var gjord och betald.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api import leads as leads_api
from app.jobs.store import MemoryJobStore
from tests.test_korning_samtidighet import TENANT, TID, _k, _ny_korning, _VaxlandeStorage

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _utan_paus(monkeypatch):
    monkeypatch.setattr(leads_api, "_RAPPORT_PAUSER_S", (0.0, 0.0))


class _SkakigtJobblager(MemoryJobStore):
    """`complete` kastar de första `fel_antal` gångerna."""

    def __init__(self, fel_antal: int) -> None:
        super().__init__()
        self.fel_kvar = fel_antal
        self.forsok = 0

    async def complete(self, job_id, result):
        self.forsok += 1
        if self.fel_kvar > 0:
            self.fel_kvar -= 1
            raise ConnectionError("Redis: anslutningen bröts")
        return await super().complete(job_id, result)


async def _rapportera(app_state, job_id: str, barn: str = "barn-1") -> None:
    await leads_api._rapportera_till_korning(
        app_state, TENANT, job_id, job_id=barn, namn="Ett AB", leverbar=True, skal=None, fyll=False
    )


async def test_ett_tillfalligt_fel_tappar_inte_rapporten():
    storage = _VaxlandeStorage()  # färska läsningar, som Postgres och Redis ger
    jobb = _SkakigtJobblager(fel_antal=1)
    app_state = SimpleNamespace(jobs=jobb, storage=storage, leadsstrom=None)
    job_id = await _ny_korning(storage, [], mal=5, pagaende=1)

    await _rapportera(app_state, job_id)

    rad = await storage.get_leads_korning(TID, job_id)
    assert rad["status"] == "processing", "körningen får inte fällas av ett tillfälligt fel"
    k = rad["korning"]
    assert k["rapporterade"] == ["barn-1"]
    assert k["levererade"] == 1 and k["pagaende"] == 0
    assert jobb.forsok == 2


async def test_omforsoket_raknar_inte_utfallet_tva_ganger():
    """Skrivningen till Redis lyckas men liggaren faller: nästa försök ska
    spara liggaren utan att räkna in samma barn en gång till."""
    storage = _VaxlandeStorage()  # färska läsningar, som Postgres och Redis ger
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    job_id = await _ny_korning(storage, [], mal=5, pagaende=1)
    riktig = storage.set_leads_job_status
    fel_kvar = [1]

    async def _skakig(*a, **k):
        if fel_kvar[0] > 0:
            fel_kvar[0] -= 1
            raise TimeoutError("databasen svarade inte")
        return await riktig(*a, **k)

    storage.set_leads_job_status = _skakig  # type: ignore[method-assign]

    await _rapportera(app_state, job_id)

    k = await _k(storage, job_id)
    assert k["rapporterade"] == ["barn-1"]
    assert k["levererade"] == 1 and k["undersokta"] == 1


async def test_ihallande_fel_faller_korningen_med_orsak():
    storage = _VaxlandeStorage()  # färska läsningar, som Postgres och Redis ger
    jobb = _SkakigtJobblager(fel_antal=99)
    app_state = SimpleNamespace(jobs=jobb, storage=storage, leadsstrom=None)
    job_id = await _ny_korning(storage, [], mal=5, pagaende=1)

    await _rapportera(app_state, job_id)  # kastar aldrig

    rad = await storage.get_leads_korning(TID, job_id)
    assert rad["status"] == "failed"
    assert jobb.forsok == 3, "tre försök, sedan ger rapporten upp"
