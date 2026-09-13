"""Städaren och strömmens leveranstak: inget leads-arbete står i
processing/byggs för evigt.

Testarens fynd 2026-09-13: en leadslista stod i "byggs" i dagar med tre
halvfärdiga rader. Liggaren (migration 059) och listraden (060) hade ingen
tidsgräns, och strömmen (app/jobs/stream.py) kvitterade en post som nått
MAX_LEVERANSER tyst. Se app/jobs/stadare.py.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fakeredis.aioredis as fakeredis_aio
import pytest

from app.api import leads as leads_api
from app.jobs import stadare
from app.jobs import stream as stream_mod
from app.jobs.store import MemoryJobStore
from app.jobs.stream import ChattStrom
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _gammal(minuter: int = 120) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minuter)).isoformat()


async def _hangande_jobb(storage, jobs, *, status="processing", alder=120, scope="research"):
    job_id = await jobs.create(tenant_id=TENANT, status="queued")
    if status == "processing":
        await jobs.start(job_id)
    await storage.set_leads_job_status(TENANT, job_id=job_id, status=status, scope=scope)
    storage.leads_job_ledger[job_id]["created_at"] = _gammal(alder)
    return job_id


async def _hangande_lista(storage, *, status="byggs", alder=120, rader=3):
    lista = await storage.create_lead_list(TENANT, titel="Hänger", icp={}, antal=10)
    await storage.set_lead_list_status(TENANT, lista["id"], status=status)
    for i in range(rader):
        await storage.add_lead_list_item(TENANT, list_id=lista["id"], company_name=f"Skräp {i} AB")
    for rad in storage.lead_lists[TENANT]:
        if rad["id"] == lista["id"]:
            rad["created_at"] = _gammal(alder)
    return lista


async def test_stadaren_avslutar_hangande_jobb_och_listor_arligt():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)

    hangande = await _hangande_jobb(storage, jobs)
    koad = await _hangande_jobb(storage, jobs, status="queued")
    farskt = await _hangande_jobb(storage, jobs, alder=5)
    klart = await _hangande_jobb(storage, jobs)
    await storage.set_leads_job_status(TENANT, job_id=klart, status="completed")
    lista = await _hangande_lista(storage)
    klar_lista = await _hangande_lista(storage, status="klar", rader=2)
    ny_lista = await _hangande_lista(storage, alder=5, rader=1)

    utfall = await stadare.stada_tenant(app_state, TENANT, minuter=60)

    assert sorted(utfall["jobb"]) == sorted([hangande, koad])
    assert utfall["listor"] == [lista["id"]]
    assert await storage.get_leads_job_status(TENANT, hangande) == "failed"
    assert await storage.get_leads_job_status(TENANT, koad) == "failed"
    assert await storage.get_leads_job_status(TENANT, farskt) == "processing"
    assert await storage.get_leads_job_status(TENANT, klart) == "completed"
    # Pollande ytor ser ett ärligt slut, inte en evig snurra.
    post = await jobs.get(koad)
    assert post["status"] == "failed" and post["error"] == stadare.HANGFEL_JOBB

    rad = await storage.get_lead_list(TENANT, lista["id"])
    assert rad["status"] == "fel" and rad["felorsak"] == stadare.HANGFEL_LISTA
    assert await storage.list_lead_list_items(TENANT, lista["id"]) == []
    # Klara och färska listor rörs inte.
    assert (await storage.get_lead_list(TENANT, klar_lista["id"]))["status"] == "klar"
    assert len(await storage.list_lead_list_items(TENANT, klar_lista["id"])) == 2
    assert (await storage.get_lead_list(TENANT, ny_lista["id"]))["status"] == "byggs"

    handelser = await storage.list_platform_events(limit=10)
    assert any("Städaren avslutade" in h["message"] for h in handelser)


async def test_stadaren_ror_inte_det_som_kors_i_processen():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)
    job_id = await _hangande_jobb(storage, jobs)
    lista = await _hangande_lista(storage)

    stadare.registrera_aktiv(job_id, lista["id"])
    try:
        utfall = await stadare.stada_tenant(app_state, TENANT, minuter=60)
    finally:
        stadare.avregistrera_aktiv(job_id, lista["id"])

    assert utfall == {"jobb": [], "listor": []}
    assert await storage.get_leads_job_status(TENANT, job_id) == "processing"


async def test_stadaren_skriver_inte_over_ett_klart_jobb_i_jobbstoren():
    """Liggaren kan ljuga åt andra hållet (en körning som hann bli klar i
    Redis men dog före liggarskrivningen). Jobbposten ska då inte flippas."""
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    job_id = await _hangande_jobb(storage, jobs)
    await jobs.complete(job_id, {"ok": True})
    await stadare.stada_tenant(SimpleNamespace(storage=storage, jobs=jobs), TENANT, minuter=60)
    assert (await jobs.get(job_id))["status"] == "completed"


async def test_nolla_stanger_av_stadningen():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    job_id = await _hangande_jobb(storage, jobs, alder=100_000)
    utfall = await stadare.stada_tenant(SimpleNamespace(storage=storage, jobs=jobs), TENANT, minuter=0)
    assert utfall == {"jobb": [], "listor": []}
    assert await storage.get_leads_job_status(TENANT, job_id) == "processing"


async def test_bakgrundsloopen_stadar_vid_forsta_varvet(monkeypatch):
    """Första varvet ÄR uppstartsstädningen — testarens fastnade jobb i
    development städas vid första deployen utan att någon rör databasen."""
    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug=f"stad-{uuid.uuid4().hex[:6]}", name="Städtest")
    jobs = MemoryJobStore()
    job_id = await jobs.create(tenant_id=tenant["id"], status="queued")
    await storage.set_leads_job_status(tenant["id"], job_id=job_id, status="processing")
    storage.leads_job_ledger[job_id]["created_at"] = _gammal(24 * 60)

    async def avbryt(_sekunder):
        raise asyncio.CancelledError

    monkeypatch.setattr(stadare.asyncio, "sleep", avbryt)
    with pytest.raises(asyncio.CancelledError):
        await stadare.run_leads_stadare(SimpleNamespace(storage=storage, jobs=jobs))

    assert await storage.get_leads_job_status(tenant["id"], job_id) == "failed"


async def test_listlasning_stadar_lat():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    lista = await _hangande_lista(storage)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(storage=storage, jobs=jobs)))

    svar = await leads_api.lista_leadslistor(request, {"tenant_id": TENANT})
    [rad] = [r for r in svar["lists"] if r["id"] == lista["id"]]
    assert rad["status"] == "fel"
    assert rad["item_count"] == 0

    detalj = await leads_api.hamta_leadslista(request, lista["id"], {"tenant_id": TENANT})
    assert detalj["list"]["felorsak"] == stadare.HANGFEL_LISTA
    assert detalj["items"] == []


# -- Strömmens leveranstak ----------------------------------------------------


async def test_uppgiven_listpost_failar_liggaren_och_listan():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)
    lista = await storage.create_lead_list(TENANT, titel="Kraschar", icp={}, antal=5)
    await storage.set_lead_list_status(TENANT, lista["id"], status="byggs")
    await storage.add_lead_list_item(TENANT, list_id=lista["id"], company_name="Halvfärdig AB")
    job_id = await jobs.create(tenant_id=TENANT, status="queued")
    await jobs.start(job_id)
    await storage.set_leads_job_status(TENANT, job_id=job_id, status="processing", scope="lista")

    await leads_api.ge_upp_leadsjobb(
        app_state,
        {"kind": "lista", "job_id": job_id, "tenant_id": TENANT, "list_id": lista["id"]},
    )

    assert await storage.get_leads_job_status(TENANT, job_id) == "failed"
    assert (await jobs.get(job_id))["error"] == stadare.UPPGIVET_JOBB
    rad = await storage.get_lead_list(TENANT, lista["id"])
    assert rad["status"] == "fel" and rad["felorsak"] == stadare.UPPGIVET_LISTA
    assert await storage.list_lead_list_items(TENANT, lista["id"]) == []


async def test_uppgiven_post_for_klart_jobb_ror_ingenting():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    job_id = await jobs.create(tenant_id=TENANT)
    await jobs.complete(job_id, {"ok": True})
    await storage.set_leads_job_status(TENANT, job_id=job_id, status="completed")
    await leads_api.ge_upp_leadsjobb(
        SimpleNamespace(storage=storage, jobs=jobs),
        {"job_id": job_id, "tenant_id": TENANT, "prospect_id": "p-1", "scope": "research"},
    )
    assert await storage.get_leads_job_status(TENANT, job_id) == "completed"
    assert (await jobs.get(job_id))["status"] == "completed"


async def test_strommen_anropar_vid_uppgivet_fore_kvitteringen(monkeypatch):
    klient = fakeredis_aio.FakeRedis(decode_responses=True)
    uppgivna: list[dict] = []

    async def vid_uppgivet(payload):
        uppgivna.append(payload)

    strom = ChattStrom(klient, stream_key="crm:jobb:leads-test", vid_uppgivet=vid_uppgivet)
    try:
        msg_id = await strom.enqueue({"job_id": "j-1", "tenant_id": TENANT, "kind": "lista"})
        await klient.xreadgroup(strom.group, "dod", {strom.stream_key: ">"}, count=10)
        monkeypatch.setattr(stream_mod, "MIN_IDLE_MS", 0)
        monkeypatch.setattr(
            strom, "_leveransantal", AsyncMock(return_value={msg_id: stream_mod.MAX_LEVERANSER + 1})
        )
        hanterare = AsyncMock()

        assert await strom.atertag(hanterare) == 0

        hanterare.assert_not_awaited()
        assert uppgivna == [{"job_id": "j-1", "tenant_id": TENANT, "kind": "lista"}]
        pending = await klient.xpending(strom.stream_key, strom.group)
        assert pending["pending"] == 0
    finally:
        await klient.aclose()


async def test_trasig_vid_uppgivet_hindrar_inte_kvitteringen(monkeypatch):
    klient = fakeredis_aio.FakeRedis(decode_responses=True)
    strom = ChattStrom(
        klient,
        stream_key="crm:jobb:leads-test2",
        vid_uppgivet=AsyncMock(side_effect=RuntimeError("lagringen nere")),
    )
    try:
        msg_id = await strom.enqueue({"job_id": "j-2", "tenant_id": TENANT})
        await klient.xreadgroup(strom.group, "dod", {strom.stream_key: ">"}, count=10)
        monkeypatch.setattr(stream_mod, "MIN_IDLE_MS", 0)
        monkeypatch.setattr(
            strom, "_leveransantal", AsyncMock(return_value={msg_id: stream_mod.MAX_LEVERANSER + 1})
        )
        await strom.atertag(AsyncMock())
        pending = await klient.xpending(strom.stream_key, strom.group)
        assert pending["pending"] == 0, "posten måste kvitteras även om callbacken kastar"
    finally:
        await klient.aclose()
