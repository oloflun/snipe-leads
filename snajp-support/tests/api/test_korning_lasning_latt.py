"""Körningslistan och pauskollen läser aldrig motorns arbetsminne.

main 2026-11-07: en körning på 200 bar flera MB kandidater, listspår och
utslag i `korning`. Listan, städaren, autopiloten och motorns pauskoll före
varje bolag läste och avkodade allt det i API:ts händelseloop, och API:t
slutade svara ("Assistenten har svårt att nå sin motor"). Bara motorn själv,
som skriver tillbaka hela tillståndet, ska läsa arbetsminnet.
"""
from __future__ import annotations

import pytest

from app.api import leads as leads_api
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-0000-0000-000000000001"


def _lager_med_korning(job_id: str = "b1", status: str = "processing") -> MemoryStorage:
    s = MemoryStorage()
    s.leads_job_ledger[job_id] = {
        "job_id": job_id, "tenant_id": TENANT, "scope": "batch", "status": status,
        "is_test": False, "created_at": "2026-11-07T10:00:00+00:00",
        "korning": {
            "mal": 200, "klar": False, "styrning": "paus", "tratt": [{"namn": "A"}], "jobs": [],
            "kandidater": [{"company_name": "K"}], "listspar": [{"company_name": "L"}],
            "webbpool": {"x": 1}, "utslag": [1], "rapporterade": [1],
        },
    }
    return s


@pytest.mark.anyio
async def test_listan_skar_bort_arbetsminnet_som_standard():
    s = _lager_med_korning()
    (rad,) = await s.list_leads_korningar(TENANT)
    assert set(rad["korning"]) == {"mal", "klar", "styrning", "tratt", "jobs"}
    (full,) = await s.list_leads_korningar(TENANT, arbetsminne=True)
    assert full["korning"]["kandidater"] == [{"company_name": "K"}]


@pytest.mark.anyio
async def test_listan_filtrerar_status_och_utom():
    s = _lager_med_korning("b1")
    s.leads_job_ledger["b2"] = {**s.leads_job_ledger["b1"], "job_id": "b2", "status": "completed"}
    assert [r["job_id"] for r in await s.list_leads_korningar(TENANT, status="processing")] == ["b1"]
    assert await s.list_leads_korningar(TENANT, status="processing", utom="b1") == []


@pytest.mark.anyio
async def test_motorns_lasning_behaller_arbetsminnet():
    """Motorn läser och skriver tillbaka hela tillståndet: där får inget skäras bort."""
    s = _lager_med_korning()
    rad = await s.get_leads_korning(TENANT, "b1")
    assert rad["korning"]["listspar"] == [{"company_name": "L"}]
    latt = await s.get_leads_korning(TENANT, "b1", arbetsminne=False)
    assert "listspar" not in latt["korning"]


@pytest.mark.anyio
async def test_pauskollen_laser_bara_styrningen():
    s = _lager_med_korning()
    assert await s.get_korning_styrning(TENANT, "b1") == "paus"
    assert await s.get_korning_styrning(TENANT, "saknas") is None


@pytest.mark.anyio
async def test_andra_korningar_laser_inte_den_egna():
    s = _lager_med_korning("egen")
    anrop = []
    original = s.list_leads_korningar

    async def spion(tenant_id, **kw):
        anrop.append(kw)
        return await original(tenant_id, **kw)

    s.list_leads_korningar = spion  # type: ignore[method-assign]
    assert await leads_api._andra_korningars_bolag(s, TENANT, "egen") == set()
    assert anrop == [{"limit": 20, "arbetsminne": True, "status": "processing", "utom": "egen"}]
