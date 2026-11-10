"""Beställt antal levereras (Sebbe 2026-11-08: "om man söker 200 ska 200
hittas").

main 2026-11-08: två körningar på 200 stannade 18:43 på 33 och 68 med
slutorsak "budget". Dygnsbudgeten kontrollerades före VARJE bolag inne i
motorn, fast budget.py säger att grinden är en dörr vid starten och aldrig
en vakt inne i en beställd körning. Här:
  a) en körning som startat levererar målet även när budgeten tar slut mitt i,
  b) en avslutad körning under målet går att fortsätta och når målet utan
     att pröva samma bolag igen,
  c) en körning som nådde målet eller avbröts går inte att fortsätta.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import leads as leads_api
from app.jobs.store import MemoryJobStore
from app.leads import korning as korningsmodul
from app.storage.memory import MemoryStorage
from tests.invariants.test_inv_job_003 import TENANT, _bolag, _installera, _payload, _vanta_klar

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_budgeten_stoppar_inte_en_startad_korning(monkeypatch):
    """(a): budgeten tar slut direkt efter starten — körningen levererar ändå."""
    namn = ["Bra Ett", "Bra Två", "Bra Tre"]
    _installera(monkeypatch, [_bolag(n) for n in namn], bra=set(namn))
    storage = MemoryStorage()

    async def _slut(*_a, **_k):
        return 10**12

    monkeypatch.setattr(storage, "sum_leads_tokens", _slut)
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    job_id = await app_state.jobs.create(tenant_id=TENANT["tenant_id"], status="queued")
    await storage.set_leads_job_status(TENANT["tenant_id"], job_id=job_id, status="queued", scope="batch", is_test=True)

    await leads_api._run_batch(app_state, _payload(job_id, 3))

    klar = await _vanta_klar(storage, job_id)
    assert klar["korning"]["slut_orsak"] == "klar"
    assert klar["korning"]["levererade"] == 3


async def _avslutad_under_malet(storage: MemoryStorage, job_id: str, *, orsak: str = "budget") -> None:
    k = korningsmodul.ny_korning(mal=3, scope="research", overrides={"industries": ["Redovisning"]}, is_test=True)
    k.update(levererade=1, undersokta=1, klar=True, slut_orsak=orsak, flaskhals="För litet",
             tratt=[{"namn": "Prövad Redan", "steg": "register", "skal": "För litet: 0 anställda"}],
             jobs=[{"job_id": "x", "company_name": "Levererad Ett"}])
    await storage.set_leads_job_status(
        TENANT["tenant_id"], job_id=job_id, status="completed", scope="batch", korning=k, is_test=True
    )


async def test_en_korning_under_malet_fortsatter_till_malet(monkeypatch):
    """(b)."""
    pool = [_bolag(n) for n in ("Prövad Redan", "Bra Fyra", "Bra Fem")]
    _installera(monkeypatch, pool, bra={"Bra Fyra", "Bra Fem"})
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    await _avslutad_under_malet(storage, "b-200")

    svar = await leads_api._fortsatt_korning(app_state, TENANT, "b-200")
    assert svar["fortsatt"] is True

    klar = await _vanta_klar(storage, "b-200")
    k = klar["korning"]
    assert klar["status"] == "completed"
    assert k["slut_orsak"] == "klar"
    assert k["levererade"] == 3
    assert k["fortsatt"] == 1
    assert k["flaskhals"] is None
    # Bolaget som redan prövats i tratten prövas inte igen.
    namn = [j.get("company_name") for j in k["jobs"]]
    assert "Prövad Redan" not in namn and {"Bra Fyra", "Bra Fem"} <= set(namn)


@pytest.mark.parametrize(
    "rad",
    [
        {"scope": "batch", "status": "completed", "korning": {"mal": 3, "levererade": 3, "slut_orsak": "klar"}},
        {"scope": "batch", "status": "completed", "korning": {"mal": 3, "levererade": 1, "slut_orsak": "avbruten"}},
        {"scope": "batch", "status": "processing", "korning": {"mal": 3, "levererade": 1}},
        {"scope": "lista", "status": "completed", "korning": None},
    ],
)
def test_vad_som_inte_kan_fortsatta(rad):
    """(c)."""
    assert leads_api._kan_fortsatta(rad) is False


def test_budgetstoppad_kan_fortsatta():
    rad = {"scope": "batch", "status": "completed", "korning": {"mal": 200, "levererade": 33, "slut_orsak": "budget"}}
    assert leads_api._kan_fortsatta(rad) is True


async def test_fortsatt_svarar_409_pa_en_klar_korning():
    storage = MemoryStorage()
    app_state = SimpleNamespace(jobs=MemoryJobStore(), storage=storage, leadsstrom=None)
    await _avslutad_under_malet(storage, "b-avbruten", orsak="avbruten")
    with pytest.raises(HTTPException) as fel:
        await leads_api._fortsatt_korning(app_state, TENANT, "b-avbruten")
    assert fel.value.status_code == 409
