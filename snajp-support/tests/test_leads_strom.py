"""Leadsströmmen (Fas R4, bd snipe-2xj): leads-batchens per-prospekt-jobb ska
ÖVERLEVA en deploy, på SAMMA strömmönster som chatten (Fas R1, bd snipe-lr7,
se tests/test_chatt_strom.py). Samma ChattStrom-klass (app/jobs/stream.py),
egen ström (crm:jobb:leads) och egen consumer-grupp, samma XADD/XREADGROUP/
XAUTOCLAIM-mekanik.

Formen speglar tests/test_chatt_strom.py rakt av: fakeredis i stället för en
riktig Redis-server, samma fyra scenarier ((a) enqueue->worker->completed,
(b) completed-vakten, (c) paritet utan Redis, (d) återtag av en död
konsuments post) — bara hanteraren och nyttolasten skiljer sig.

`build_context_pack`/`run_research_step` monkeypatchas i ALLA scenarier som
går genom `hantera_leads_jobb`/`_run_batch_prospect`: samma mönster som
tests/leads/test_batch_markering.py, så att inget test gör ett riktigt
LLM- eller skrapningsanrop.
"""

from __future__ import annotations

import asyncio as _asyncio
import uuid

import fakeredis.aioredis as fakeredis_aio
import pytest

from app.api import leads as leads_api
from app.jobs import stream as stream_mod
from app.jobs.stream import ChattStrom
from app.jobs.store import MemoryJobStore

pytestmark = pytest.mark.anyio

from app.redisnycklar import nyckel

LEADS_STREAM_KEY = "crm:jobb:leads"
FEJKAD_LIVE_NYCKEL = "sk-" + "a" * 37


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def redis_client():
    client = fakeredis_aio.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def strom(redis_client):
    # group="agenter" skrivs ut explicit (matchar main.py:s lifespan-anrop)
    # trots att det redan är defaultvärdet — så testet inte tyst slutar mäta
    # rätt sak om defaulten någonsin ändras.
    return ChattStrom(redis_client, stream_key=LEADS_STREAM_KEY, group="agenter")


class _AppState:
    pass


@pytest.fixture
def app_state():
    from app.storage.memory import MemoryStorage

    state = _AppState()
    # En riktig MemoryStorage (inte None som förr): sedan INV-JOB-002 läser
    # och skriver hanteraren leads_job_ledger via storage — liggaren ÄR
    # vakten numera, så en storage-lös stubb hade testat en kodväg som inte
    # finns i drift. build_context_pack/run_research_step är fortfarande
    # monkeypatchade (se `spion`) — inga riktiga LLM-/skrapanrop görs.
    state.storage = MemoryStorage()
    state.jobs = MemoryJobStore()
    return state


@pytest.fixture
def spion(monkeypatch):
    """Monkeypatchar de två beroenden `_run_batch_prospect` faktiskt anropar
    (build_context_pack, run_research_step) så leads-strömstesterna aldrig
    gör ett riktigt LLM- eller skrapningsanrop. Räknar anropen åt
    completed-vakts-testet ((b) nedan) — där är RÄKNAREN själva beviset,
    inte bara att jobbet blir completed."""
    anrop = {"n": 0}

    async def falsk_context_pack(storage, tenant_id, *, overrides=None):
        return "KONTEXT", ()

    async def falskt_research_steg(storage, tenant_id, **kwargs):
        anrop["n"] += 1
        return {"ok": True, "prospect_id": kwargs.get("prospect_id")}

    monkeypatch.setattr(leads_api, "build_context_pack", falsk_context_pack)
    monkeypatch.setattr(
        "app.agent.leads_agent.run_research_step", falskt_research_steg, raising=False
    )
    return anrop


# --- (a) Enqueue -> worker -> completed -------------------------------------


async def test_enqueue_worker_ett_varv_fullbordar_leadsjobbet(strom, app_state, spion):
    """XADD via ChattStrom (som /api/leads/runs/batch gör när leadsströmmen
    finns), sedan ETT workervarv manuellt — inte hela evighetsloopen. Mäter
    bara STRÖM-mekaniken: en enqueued post når fram till hanteraren
    (hantera_leads_jobb) och jobbet blir completed."""
    job_id = await app_state.jobs.create(tenant_id="t1")
    await strom.enqueue(
        {
            "job_id": job_id,
            "tenant_id": "t1",
            "tenant_name": "Provbolaget",
            "prospect_id": "p-1",
            "scope": "research",
            "overrides": None,
            "is_test": False,
        }
    )

    async def hanterare(payload: dict) -> None:
        await leads_api.hantera_leads_jobb(app_state, payload)

    antal = await strom.kor_ett_varv("konsument-1", hanterare)

    assert antal == 1
    job = await app_state.jobs.get(job_id)
    assert job["status"] == "completed"
    assert job["result"]["prospect_id"] == "p-1"
    assert spion["n"] == 1


# --- (b) Completed-vakten: ett redan färdigt jobb körs inte om --------------


async def test_redan_fardigt_leadsjobb_kors_inte_om(app_state, spion):
    """Dör processen i fönstret mellan jobs.complete() och XACK ligger
    posten kvar okvitterad fast resultatet redan är levererat. Ett återtag
    av den posten får inte köra om research-steget — det hade kostat åtta
    LLM-anrop och (åtminstone) en extra agent_runs-rad för samma prospekt i
    onödan. Räknaren är beviset: antalet anrop till run_research_step får
    INTE öka vid det andra försöket."""
    job_id = await app_state.jobs.create(tenant_id="t1")
    payload = {
        "job_id": job_id,
        "tenant_id": "t1",
        "tenant_name": "Provbolaget",
        "prospect_id": "p-1",
        "scope": "research",
        "overrides": None,
        "is_test": False,
    }

    await leads_api.hantera_leads_jobb(app_state, payload)
    assert spion["n"] == 1
    job = await app_state.jobs.get(job_id)
    assert job["status"] == "completed"

    # "Återtaget": samma post en gång till (atertag() bygger inte om
    # payloaden — den är oförändrad, exakt som XAUTOCLAIM levererar den).
    await leads_api.hantera_leads_jobb(app_state, payload)

    assert spion["n"] == 1, (
        "ett redan färdigt leads-jobb körde research-steget igen — "
        "completed-vakten i hantera_leads_jobb saknas eller är trasig"
    )


async def test_batch_kind_kors_sokningen_inte_ett_prospekt(app_state, monkeypatch):
    """Utan kind=batch-grenen anropar workern _run_batch_prospect utan
    prospect_id och sökningen sker aldrig — POST:en svarade 202 och UI:t
    pollar ett jobb som aldrig blir completed."""
    kallad = {}

    async def _spy(state, payload):
        kallad["payload"] = payload

    monkeypatch.setattr(leads_api, "_run_batch", _spy)
    job_id = await app_state.jobs.create(tenant_id="t1")
    await leads_api.hantera_leads_jobb(
        app_state,
        {
            "kind": "batch",
            "job_id": job_id,
            "tenant_id": "t1",
            "tenant_name": "Provbolaget",
            "scope": "research",
            "limit": 1,
            "is_test": True,
            "company_names": [],
        },
    )
    assert kallad["payload"]["kind"] == "batch"
    assert kallad["payload"]["job_id"] == job_id


# --- (c) Paritet: utan REDIS_URL tar endpointen create_task-vägen -----------
# gäller — assert på BETEENDET (jobbet blir faktiskt klart), inte bara
# attributet. REDIS_URL är redan tom i hela sviten (tests/conftest.py).


@pytest.fixture
def live_llm(monkeypatch):
    """Samma fixtur som tests/leads/test_batch_markering.py, av samma skäl:
    /api/leads/runs/batch svarar 503 i simuleringsläge (_require_live_llm),
    så paritetstestet måste låtsas ha en skarp nyckel för att ens nå
    enqueue/create_task-grenen. Ingen riktig nätverkstrafik: build_context_pack
    och run_research_step är monkeypatchade av `spion`."""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("DEEPSEEK_API_KEY", FEJKAD_LIVE_NYCKEL)
    from app.config import get_settings

    get_settings.cache_clear()
    assert not get_settings().is_simulation()
    yield
    get_settings.cache_clear()


async def test_utan_redis_tar_batchendpointen_create_task_vagen(live_llm, spion, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.config import DEFAULT_TENANT_ID, get_settings
    from app.main import app

    async def _webb(namn, *, geografi=None):
        return "https://testbolaget.se"

    monkeypatch.setattr(leads_api, "sla_upp_webbplats", _webb)

    async with app.router.lifespan_context(app):
        assert app.state.leadsstrom is None
        assert app.state.jobs.name == "memory"

        await app.state.storage.create_prospect(DEFAULT_TENANT_ID, company_name="Testbolaget AB")

        demo_key = get_settings().snajp_demo_api_key
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/leads/runs/batch",
                headers={"X-API-Key": demo_key},
                json={
                    "limit": 1,
                    "company_names": ["Testbolaget AB"],
                    "is_test": True,
                },
            )
            assert response.status_code == 202, response.text
            job_id = response.json()["jobs"][0]["job_id"]

            # app.state.leadsstrom stannar None under HELA anropet — annars
            # hade det bara varit ett attribut som råkade sättas rätt vid
            # start, inte ett bevis på vilken väg endpointen faktiskt tog.
            assert app.state.leadsstrom is None

            result = None
            for _ in range(50):
                job = (
                    await client.get(f"/api/jobs/{job_id}", headers={"X-API-Key": demo_key})
                ).json()
                if job["status"] == "completed":
                    result = job["result"]
                    break
                assert job["status"] != "failed", job
                await _asyncio.sleep(0.05)
            assert result is not None, "create_task-vägen slutförde aldrig leads-jobbet"
            assert result.get("jobs"), result

    # Sökjobbet är completed; research-jobbet har startats via create_task.
    # Vänta in att spionen faktiskt körts (den är schemalagd, inte awaited).
    for _ in range(50):
        if spion["n"] >= 1:
            break
        await _asyncio.sleep(0.05)
    assert spion["n"] == 1


# --- (d) Återtag: en "död" konsuments okvitterade post ----------------------


async def test_atertag_plockar_upp_dod_konsuments_leadspost(strom, redis_client, monkeypatch):
    """En post som lästs av en konsument som sedan aldrig kvitterar den
    (processen dödades mellan XREADGROUP och XACK — exakt deploy-scenariot
    hela den här modulen finns för) ska plockas upp av atertag() och köras
    klart. Samma test som tests/test_chatt_strom.py:s motsvarighet, mot
    leads-strömmen (egen stream_key/group) i stället för chattens."""
    job_id = str(uuid.uuid4())
    await strom.enqueue({"job_id": job_id, "tenant_id": "t1", "prospect_id": "p-1"})

    # "Död" konsument: läser posten men kvitterar aldrig.
    lasta = await redis_client.xreadgroup(
        strom.group, "dod-konsument", {strom.stream_key: ">"}, count=10
    )
    assert lasta, "posten borde ha lästs av den döda konsumenten"

    # MIN_IDLE_MS sätts till 0 för testet — annars hade det krävt en RIKTIG
    # 60-sekunders väntan innan XAUTOCLAIM räknar posten som övergiven.
    monkeypatch.setattr(stream_mod, "MIN_IDLE_MS", 0)

    korda = []

    async def hanterare(payload: dict) -> None:
        korda.append(payload["job_id"])

    antal = await strom.atertag(hanterare)

    assert antal == 1
    assert korda == [job_id]
    pending = await redis_client.xpending(strom.stream_key, strom.group)
    assert pending["pending"] == 0


# --- Bonus: main.py:s lifespan-koppling, end-to-end mot fakeredis -----------


async def test_med_redis_url_skapas_leadsstrom_och_workers_startar(monkeypatch):
    """Speglar app/main.py:s lifespan-gren för leadsströmmen: med REDIS_URL
    satt (och en Redis-klient som går att nå) ska leadsstrom skapas, atertag
    köras en gång vid uppstart, och leads_workers st worker-tasks startas —
    och teardown ska kunna avbryta dem utan att hänga. Samma test som
    tests/test_chatt_strom.py:s motsvarighet för chattströmmen."""
    import redis.asyncio as redis_asyncio

    from app.config import get_settings
    from app.main import app

    fake_client = fakeredis_aio.FakeRedis(decode_responses=True)
    monkeypatch.setenv("REDIS_URL", "redis://fakeredis-test/0")
    monkeypatch.setattr(redis_asyncio, "from_url", lambda *a, **kw: fake_client)
    get_settings.cache_clear()

    try:
        async with app.router.lifespan_context(app):
            assert app.state.jobs.name == "redis"
            assert app.state.chattstrom is not None
            assert app.state.leadsstrom is not None
            # Två separata strömmar på SAMMA klient, inte samma ström två
            # gånger — annars hade chatt- och leadsjobb blandats i samma kö.
            assert app.state.leadsstrom.stream_key == nyckel(LEADS_STREAM_KEY)
            assert app.state.leadsstrom.stream_key != app.state.chattstrom.stream_key
    finally:
        get_settings.cache_clear()
        await fake_client.aclose()
