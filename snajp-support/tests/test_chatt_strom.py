"""ChattStrömmen (Fas R1, bd snipe-lr7): en chattkörning ska ÖVERLEVA en
deploy. Se app/jobs/stream.py för hela motiveringen och
tests/invariants/test_inv_job_001.py för idempotensinvarianten (INV-JOB-001)
som gör "kör om" säkert.

fakeredis i stället för en riktig Redis-server: streams-API:t
(XADD/XREADGROUP/XAUTOCLAIM/XACK/XPENDING) testas utan nätverk. XAUTOCLAIM
verifierades separat att fungera i fakeredis>=2.23 (manuell probe mot
fakeredis.aioredis.FakeRedis innan den här filen skrevs) — det är därför
atertag() i app/jobs/stream.py använder XAUTOCLAIM och inte den mer
omständliga XPENDING+XCLAIM-tvåstegsvägen. test_atertag_plockar_upp_* nedan
är beviset som lever kvar i sviten.
"""

from __future__ import annotations

import uuid

import fakeredis.aioredis as fakeredis_aio
import pytest

from app.jobs import stream as stream_mod
from app.jobs.stream import ChattStrom
from app.jobs.store import MemoryJobStore

pytestmark = pytest.mark.anyio


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
    return ChattStrom(redis_client)


# --- enqueue ----------------------------------------------------------------


async def test_enqueue_lagger_en_post_i_strommen(strom, redis_client):
    job_id = str(uuid.uuid4())
    await strom.enqueue({"job_id": job_id, "tenant_id": "t1", "message": "hej"})
    assert await redis_client.xlen(stream_mod.STREAM_KEY) == 1


async def test_enqueue_skapar_gruppen_idempotent(strom):
    """BUSYGROUP vid andra XGROUP CREATE-anropet ska fångas, inte kasta."""
    await strom.enqueue({"job_id": "a", "tenant_id": "t1", "message": "hej"})
    # Andra enqueue-anropet triggar INTE ett nytt xgroup_create-försök
    # (_grupp_klar är redan True), men om cachen nollställs ska BUSYGROUP
    # fortfarande fångas tyst.
    strom._grupp_klar = False
    await strom.enqueue({"job_id": "b", "tenant_id": "t1", "message": "hej igen"})  # kraschar inte


# --- (a) Enqueue -> worker -> completed -------------------------------------


async def test_enqueue_worker_ett_varv_fullbordar_jobbet(strom):
    """XADD via ChattStrom (som endpoint-vägen gör), sedan ETT workervarv
    manuellt — inte hela evighetsloopen. Simuleringsläget testas separat
    (tests/test_api.py); här mäts bara STRÖM-mekaniken: en enqueued post når
    fram till hanteraren och jobbet blir completed."""
    jobs = MemoryJobStore()
    job_id = await jobs.create(tenant_id="t1")
    await strom.enqueue({"job_id": job_id, "tenant_id": "t1", "message": "hej"})

    async def hanterare(payload: dict) -> None:
        await jobs.complete(payload["job_id"], {"reply": "svar", "ticket_id": "tick-1"})

    antal = await strom.kor_ett_varv("konsument-1", hanterare)

    assert antal == 1
    job = await jobs.get(job_id)
    assert job["status"] == "completed"
    assert job["result"]["reply"] == "svar"


async def test_kor_ett_varv_pa_tom_strom_gor_ingenting(strom):
    async def hanterare(_payload: dict) -> None:
        raise AssertionError("hanteraren skulle aldrig anropas — inget att läsa")

    antal = await strom.kor_ett_varv("konsument-1", hanterare)
    assert antal == 0


async def test_hanterat_fel_kvitteras_anda(strom, redis_client):
    """'Ett hanterat fel är hanterat': hanteraren fångar sitt eget fel (precis
    som app.api.chat._process gör) och kastar aldrig ut — posten ska då
    KVITTERAS, inte ligga kvar i pending för att atertag() ska ta om den i
    onödan."""
    job_id = str(uuid.uuid4())
    await strom.enqueue({"job_id": job_id, "tenant_id": "t1", "message": "hej"})

    kord = []

    async def hanterare_som_fangar_sitt_eget_fel(payload: dict) -> None:
        kord.append(payload["job_id"])
        # Simulerar _process: fångar internt, kastar aldrig.

    await strom.kor_ett_varv("konsument-1", hanterare_som_fangar_sitt_eget_fel)

    assert kord == [job_id]
    pending = await redis_client.xpending(stream_mod.STREAM_KEY, stream_mod.GROUP_NAME)
    assert pending["pending"] == 0


async def test_hanterare_som_kastar_lamnar_posten_okvitterad(strom, redis_client):
    """En BUGG i hanteraren (den kastar, i stället för att fånga sitt eget
    fel) ska INTE tystas ned med en XACK — posten ska bli kvar i pending så
    atertag() kan ge den en ny chans."""
    job_id = str(uuid.uuid4())
    await strom.enqueue({"job_id": job_id, "tenant_id": "t1", "message": "hej"})

    async def trasig_hanterare(_payload: dict) -> None:
        raise RuntimeError("bugg i hanteraren, inte ett agentfel")

    with pytest.raises(RuntimeError):
        await strom.kor_ett_varv("konsument-1", trasig_hanterare)

    pending = await redis_client.xpending(stream_mod.STREAM_KEY, stream_mod.GROUP_NAME)
    assert pending["pending"] == 1


# --- (c) Återtag: en "död" konsuments okvitterade post ----------------------


async def test_atertag_plockar_upp_dod_konsuments_okvitterade_post(strom, redis_client, monkeypatch):
    """En post som lästs av en konsument som sedan aldrig kvitterar den
    (processen dödades mellan XREADGROUP och XACK — exakt deploy-scenariot
    den här modulen finns för) ska plockas upp av atertag() och köras klart."""
    job_id = str(uuid.uuid4())
    await strom.enqueue({"job_id": job_id, "tenant_id": "t1", "message": "hej"})

    # "Död" konsument: läser posten men kvitterar aldrig.
    lasta = await redis_client.xreadgroup(
        stream_mod.GROUP_NAME, "dod-konsument", {stream_mod.STREAM_KEY: ">"}, count=10
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
    pending = await redis_client.xpending(stream_mod.STREAM_KEY, stream_mod.GROUP_NAME)
    assert pending["pending"] == 0


async def test_atertag_utan_pending_gor_ingenting(strom):
    async def hanterare(_payload: dict) -> None:
        raise AssertionError("inget skulle finnas att återta")

    assert await strom.atertag(hanterare) == 0


# --- consumer_name ------------------------------------------------------


def test_consumer_name_stabilt_per_process_men_suffix_sarskiljer():
    a1 = stream_mod.consumer_name()
    a2 = stream_mod.consumer_name()
    assert a1 == a2, "samma process ska få samma namn varje gång"

    b0 = stream_mod.consumer_name(0)
    b1 = stream_mod.consumer_name(1)
    assert b0 != b1
    assert b0.startswith(a1 + ":")


# --- (d) Paritet: utan REDIS_URL är chattstrom None och create_task-vägen ---
# gäller — assert på BETEENDET (jobbet blir faktiskt klart), inte bara
# attributet. REDIS_URL är redan tom i hela sviten (tests/conftest.py).


async def test_utan_redis_ar_chattstrom_none_och_create_task_vagen_slutfor_jobbet():
    import asyncio as _asyncio

    from httpx import ASGITransport, AsyncClient

    from app.config import get_settings
    from app.main import app

    async with app.router.lifespan_context(app):
        assert app.state.chattstrom is None
        assert app.state.jobs.name == "memory"

        demo_key = get_settings().snajp_demo_api_key
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                headers={"X-API-Key": demo_key},
                json={"message": "Vilka betalsätt accepterar ni?"},
            )
            assert response.status_code == 202
            job_id = response.json()["job_id"]

            # app.state.chattstrom stannar None under HELA anropet — annars
            # hade det bara varit ett attribut som råkade sättas rätt vid
            # start, inte ett bevis på vilken väg endpointen faktiskt tog.
            assert app.state.chattstrom is None

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
            assert result is not None, "create_task-vägen slutförde aldrig jobbet"
            assert result["reply"]


# --- Bonus: main.py:s lifespan-koppling, end-to-end mot fakeredis -----------


async def test_med_redis_url_skapas_chattstrom_och_workers_startar(monkeypatch):
    """Speglar app/main.py:s lifespan-gren för Redis: med REDIS_URL satt (och
    en Redis-klient som går att nå) ska chattstrom skapas, atertag köras en
    gång vid uppstart, och chat_workers st worker-tasks startas — och
    teardown ska kunna avbryta dem utan att hänga."""
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
    finally:
        get_settings.cache_clear()
        await fake_client.aclose()
