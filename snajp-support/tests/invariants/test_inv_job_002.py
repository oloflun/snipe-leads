"""INV-JOB-002 — Ett färdigt leads-jobb körs aldrig om: liggaren i Postgres
är sanningen, inte Redis-postens TTL.

## Buggen den här stänger

Vakten i app/api/leads.hantera_leads_jobb läste BARA Redis-jobbposten, och
den ljuger för köade batchjobb på två sätt:

  1. RedisJobStore.get auto-failade "processing"-poster efter 300 s — men
     jobbraden skapades när prospektet KÖADES, inte när arbetet började.
     Med leads_workers=1 står jobb nr 5+ i en 18-jobbsbatch i kö längre än
     så och flippade till "failed" innan sitt första LLM-anrop.
  2. Posten TTL:ar bort helt efter 3 600 s.

Vid ett XAUTOCLAIM-återtag (varje worker-varv + startsvepet vid varje
deploy) såg vakten då "failed" eller ingenting — aldrig "completed" — och
körde om HELA research+utkast-kedjan. Uppmätt 2026-09-01: en färdig batch om
18 leads kördes om i sin helhet efter en omstart, ~18 kr utan handling.

Skyddet är tredelat och testas här:
  a) leads-jobb skapas som "queued" och auto-failas ALDRIG av kötid,
  b) 300-sekundersklockan räknar från start() — faktisk arbetstid,
  c) vakten läser leads_job_ledger (migration 059) FÖRST: en completed-rad
     där stoppar omkörningen även när Redis-posten är failed eller borta.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.api.leads import hantera_leads_jobb
from app.jobs.store import JOB_TIMEOUT_SECONDS, MemoryJobStore
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _AppState:
    pass


def _payload(job_id: str) -> dict:
    return {
        "job_id": job_id,
        "tenant_id": TENANT,
        "tenant_name": "Testbolaget",
        "prospect_id": "00000000-0000-4000-a000-00000000p001",
        "scope": "research_and_draft",
        "overrides": None,
        "is_test": True,
    }


async def test_koat_jobb_auto_failas_inte_av_kotid():
    """(a) + (b): ett 'queued'-jobb överlever obegränsad kötid; klockan
    börjar först vid start()."""
    jobs = MemoryJobStore()
    job_id = await jobs.create(tenant_id=TENANT, status="queued")

    # Simulera att jobbet stått i kö långt över 300-sekundersgränsen.
    jobs.jobs[job_id]["created"] = time.time() - (JOB_TIMEOUT_SECONDS * 4)
    job = await jobs.get(job_id)
    assert job["status"] == "queued", (
        "kötid är inte arbetstid — ett köat jobb får aldrig auto-failas "
        "(det var halva INV-JOB-002-buggen)"
    )

    # start() flyttar klockan: gammal skapandetid spelar ingen roll längre.
    await jobs.start(job_id)
    job = await jobs.get(job_id)
    assert job["status"] == "processing"

    # ... men FAKTISK arbetstid över gränsen auto-failar som förr.
    jobs.jobs[job_id]["started"] = time.time() - (JOB_TIMEOUT_SECONDS + 5)
    job = await jobs.get(job_id)
    assert job["status"] == "failed"


async def test_chattjobbens_klocka_ar_oforandrad():
    """Regression mot INV-JOB-001: chattjobb skapas som 'processing' utan
    start() och ska auto-failas på created-klockan precis som innan."""
    jobs = MemoryJobStore()
    job_id = await jobs.create(tenant_id=TENANT)
    jobs.jobs[job_id]["created"] = time.time() - (JOB_TIMEOUT_SECONDS + 5)
    job = await jobs.get(job_id)
    assert job["status"] == "failed"


async def test_liggaren_stoppar_omkorning_nar_redisposten_ar_borta():
    """(c) Kärnfallet: liggaren säger completed, Redis-posten är borta
    (TTL efter deploy) — återtaget får INTE köra research-kedjan igen."""
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    payload = _payload("jobb-som-ttlat-bort")
    await storage.set_leads_job_status(
        TENANT,
        job_id=payload["job_id"],
        status="completed",
        scope=payload["scope"],
        prospect_id=payload["prospect_id"],
    )
    # OBS: jobbet finns INTE i jobs-storen alls — precis som efter en TTL.

    with patch("app.api.leads._run_batch_prospect", new=AsyncMock()) as kedjan:
        await hantera_leads_jobb(app_state, payload)

    kedjan.assert_not_awaited()


async def test_liggaren_stoppar_omkorning_nar_redisposten_ar_failed():
    """(c) Andra halvan: Redis-posten hann auto-failas (300-sekundersflippen
    på ett köat jobb från före migration 059) men liggaren vet att jobbet är
    färdigt — ingen omkörning."""
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    job_id = await jobs.create(tenant_id=TENANT)
    await jobs.fail(job_id, "Tidsgräns överskriden (5 min).")
    payload = _payload(job_id)
    await storage.set_leads_job_status(
        TENANT,
        job_id=job_id,
        status="completed",
        scope=payload["scope"],
        prospect_id=payload["prospect_id"],
    )

    with patch("app.api.leads._run_batch_prospect", new=AsyncMock()) as kedjan:
        await hantera_leads_jobb(app_state, payload)

    kedjan.assert_not_awaited()


async def test_ofardigt_jobb_kors_fortfarande():
    """Kontrollfall: en liggarrad som INTE är completed (queued/processing/
    failed) släpper igenom körningen — återtaget av en faktiskt halvkörd
    batch är hela poängen med strömmen och ska fortsätta fungera."""
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    job_id = await jobs.create(tenant_id=TENANT, status="queued")
    payload = _payload(job_id)
    await storage.set_leads_job_status(
        TENANT,
        job_id=job_id,
        status="queued",
        scope=payload["scope"],
        prospect_id=payload["prospect_id"],
    )

    with patch("app.api.leads._run_batch_prospect", new=AsyncMock()) as kedjan:
        await hantera_leads_jobb(app_state, payload)

    kedjan.assert_awaited_once()
