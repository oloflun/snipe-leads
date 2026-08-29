"""Fas R2 (bd snipe-cku) — embeddingcache, svarscache och versionering.

INV-CACHE-001 själva (grinden körd genom `run_support_agent`, med mockat
LLM) står i `tests/invariants/test_inv_cache_001.py`. Den här filen testar
cache-modulerna ISOLERAT: paritet (embeddingcache), MinnesSvarscache-logiken
(tröskel, tenant/version-isolering) och att RedisSvarscache är GRACEFUL mot
ett fel — `fakeredis` stödjer inte `FT.*`, så RedisSvarscache-testerna
bevisar felvägen, inte paritetslogiken (den bevisas i MinnesSvarscache, som
körs mot riktiga vektorer här). En liveverifiering mot en riktig Redis med
Query Engine görs separat av huvudsessionen.
"""

from __future__ import annotations

import math

import pytest

from app.cache import embeddingcache, svarscache, versioner

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fresh_cache_state():
    """Varje test kör mot en FÄRSK MinnesEmbeddingCache/MinnesSvarscache/
    processräknare — annars läcker poster mellan tester, precis som en delad
    global normalt skulle."""
    embeddingcache.konfigurera(None)
    svarscache.konfigurera(None)
    versioner.konfigurera(None)
    yield
    embeddingcache.konfigurera(None)
    svarscache.konfigurera(None)
    versioner.konfigurera(None)


def _vektor(*varden: float) -> list[float]:
    return list(varden)


# --- Embeddingcache: paritet ------------------------------------------------


class _RaknandeEmbeddingKlient:
    """Fejkar `AsyncOpenAI`s `.embeddings.create(...)`-yta, räknar anrop."""

    def __init__(self) -> None:
        self.calls = 0
        self.embeddings = self

    async def create(self, *, model, input, dimensions):
        self.calls += 1
        # Deterministisk men textberoende — samma text ska ge samma vektor,
        # annars vore paritetstestet meningslöst.
        bas = float(len(input) % 7 + 1)
        return type(
            "R",
            (),
            {"data": [type("D", (), {"embedding": [bas, bas * 2, bas * 3]})()]},
        )()


@pytest.mark.anyio
async def test_samma_text_gor_bara_ett_embedding_anrop(monkeypatch):
    """Paritet embeddingcache: andra anropet med SAMMA text gör NOLL nya
    embedding-anrop — vektorn kom ur cachen."""
    from app.agent import embeddings as embeddings_modul

    klient = _RaknandeEmbeddingKlient()
    monkeypatch.setattr(embeddings_modul, "get_embedding_client", lambda: klient)

    v1 = await embeddings_modul.embed_text("Hur långt är retur-fönstret?")
    assert klient.calls == 1
    v2 = await embeddings_modul.embed_text("Hur långt är retur-fönstret?")
    assert klient.calls == 1, "Andra anropet med samma text gjorde ett nytt embedding-anrop."
    assert v1 == v2


@pytest.mark.anyio
async def test_annan_text_gor_ett_nytt_anrop(monkeypatch):
    from app.agent import embeddings as embeddings_modul

    klient = _RaknandeEmbeddingKlient()
    monkeypatch.setattr(embeddings_modul, "get_embedding_client", lambda: klient)

    await embeddings_modul.embed_text("Fråga A")
    await embeddings_modul.embed_text("En helt annan fråga B")
    assert klient.calls == 2


@pytest.mark.anyio
async def test_ingen_klient_ger_ingen_cachning_och_inget_krasch(monkeypatch):
    from app.agent import embeddings as embeddings_modul

    monkeypatch.setattr(embeddings_modul, "get_embedding_client", lambda: None)
    assert await embeddings_modul.embed_text("vad som helst") is None


@pytest.mark.anyio
async def test_redis_embeddingcache_rondtrip_binart():
    """RedisEmbeddingCache lagrar binärpackad float32 (struct), inte JSON —
    GET/SET/EXPIRE är vanliga Redis-kommandon som `fakeredis` stödjer fullt
    ut (till skillnad från `FT.*`, se RedisSvarscache-testerna nedan)."""
    import fakeredis.aioredis as fakeredis_aio

    client = fakeredis_aio.FakeRedis(decode_responses=False)
    cache = embeddingcache.RedisEmbeddingCache(client)

    assert await cache.get("hej") is None
    vektor = [0.5, -0.25, 1.0, 3.75]
    await cache.set("hej", vektor)
    hamtad = await cache.get("hej")
    assert hamtad is not None
    for a, b in zip(hamtad, vektor):
        assert math.isclose(a, b, rel_tol=1e-6)


# --- Grind och normalisering ------------------------------------------------


def test_lookup_behorig_kraver_alla_fyra_villkor():
    ok = dict(history=[], attachments=[], fakta=[], message="Hur lång är leveranstiden?")
    assert svarscache.lookup_behorig(**ok)

    assert not svarscache.lookup_behorig(**{**ok, "history": [{"id": "t1"}]})
    assert not svarscache.lookup_behorig(**{**ok, "attachments": ["data:image/png;base64,x"]})
    assert not svarscache.lookup_behorig(**{**ok, "fakta": ["Har en Android-telefon"]})


def _med_kontrollsiffra(nio: str) -> str:
    """Bygger ett Luhn-giltigt tionummer ur nio siffror. Samma konstruktion
    som tests/test_maskering.py — dupliceras hellre än importeras mellan
    testfiler, så de två inte kan glida isär av misstag."""
    summa = 0
    for i, tecken in enumerate(nio):
        varde = int(tecken) * (2 if i % 2 == 0 else 1)
        summa += varde - 9 if varde > 9 else varde
    return nio + str((10 - summa % 10) % 10)


def test_lookup_behorig_fangar_personnummer():
    giltigt = _med_kontrollsiffra("850101123")
    text = f"Mitt personnummer är {giltigt[:6]}-{giltigt[6:]}, kan ni hjälpa mig?"
    assert not svarscache.lookup_behorig(history=[], attachments=[], fakta=[], message=text)


@pytest.mark.parametrize(
    "text,vantat",
    [
        ("  Hur   Länge   Gäller   Garantin?  ", "hur länge gäller garantin?"),
        ("REDAN NORMAL", "redan normal"),
        ("", ""),
    ],
)
def test_normalisera_fraga(text, vantat):
    assert svarscache.normalisera_fraga(text) == vantat


def test_cachebara_kategorier_ar_en_delmangd_av_taxonomin():
    from app.config import CATEGORIES

    assert svarscache.CACHEBARA_KATEGORIER <= set(CATEGORIES)
    assert "betalning" not in svarscache.CACHEBARA_KATEGORIER
    assert "retur_reklamation" not in svarscache.CACHEBARA_KATEGORIER
    assert "ovrigt" not in svarscache.CACHEBARA_KATEGORIER


# --- MinnesSvarscache: tröskel och isolering --------------------------------


@pytest.mark.anyio
async def test_minnessvarscache_traff_over_troskel():
    cache = svarscache.MinnesSvarscache()
    post = svarscache.CachePost(
        tenant=TENANT_A,
        kbv="1",
        cfgv="1:1",
        vektor=(1.0, 0.0, 0.0),
        fraga_norm="hur lång är leveranstiden?",
        svar="2-4 vardagar.",
        kategori="leverans",
    )
    await cache.store(post)

    traff = await cache.lookup(tenant=TENANT_A, kbv="1", cfgv="1:1", vektor=[1.0, 0.0, 0.0])
    assert traff is not None
    assert traff.svar == "2-4 vardagar."
    assert traff.likhet == pytest.approx(1.0)


@pytest.mark.anyio
async def test_minnessvarscache_miss_under_troskel():
    cache = svarscache.MinnesSvarscache()
    await cache.store(
        svarscache.CachePost(
            tenant=TENANT_A,
            kbv="1",
            cfgv="1:1",
            vektor=(1.0, 0.0, 0.0),
            fraga_norm="fråga",
            svar="svar",
            kategori="leverans",
        )
    )
    # Nästan ortogonal mot (1,0,0) — långt under 0.9.
    traff = await cache.lookup(tenant=TENANT_A, kbv="1", cfgv="1:1", vektor=[0.0, 1.0, 0.0])
    assert traff is None


@pytest.mark.anyio
async def test_minnessvarscache_isolerar_tenant_kbv_cfgv():
    cache = svarscache.MinnesSvarscache()
    post = svarscache.CachePost(
        tenant=TENANT_A,
        kbv="1",
        cfgv="1:1",
        vektor=(1.0, 0.0, 0.0),
        fraga_norm="fråga",
        svar="svar för tenant A",
        kategori="leverans",
    )
    await cache.store(post)

    # Annan tenant — samma vektor, samma kbv/cfgv — INGEN träff.
    assert await cache.lookup(tenant=TENANT_B, kbv="1", cfgv="1:1", vektor=[1.0, 0.0, 0.0]) is None
    # Samma tenant, KB-versionen har bumpats — INGEN träff.
    assert await cache.lookup(tenant=TENANT_A, kbv="2", cfgv="1:1", vektor=[1.0, 0.0, 0.0]) is None
    # Samma tenant, konfigversionen har bumpats — INGEN träff.
    assert await cache.lookup(tenant=TENANT_A, kbv="1", cfgv="1:2", vektor=[1.0, 0.0, 0.0]) is None


@pytest.mark.anyio
async def test_forbered_utan_embeddings_ar_obehorig(monkeypatch):
    """Ingen embedding-klient => `forbered` returnerar obehörig i stället för
    att krascha eller ge en meningslös lookup."""
    from app.agent import embeddings as embeddings_modul

    monkeypatch.setattr(embeddings_modul, "get_embedding_client", lambda: None)

    kontext = await svarscache.forbered(
        TENANT_A,
        history=[],
        attachments=[],
        fakta=[],
        message="En fråga",
        kbv="1",
        cfgv="1:1",
    )
    assert kontext.behorig is False
    assert kontext.traff is None


# --- RedisSvarscache: graceful mot FT.*-fel (fakeredis stödjer inte det) ----


@pytest.mark.anyio
async def test_redis_svarscache_lookup_graceful_utan_ft(caplog):
    import fakeredis.aioredis as fakeredis_aio

    client = fakeredis_aio.FakeRedis(decode_responses=False)
    cache = svarscache.RedisSvarscache(client)

    with caplog.at_level("WARNING"):
        traff = await cache.lookup(tenant=TENANT_A, kbv="1", cfgv="1:1", vektor=[1.0, 0.0])
    assert traff is None
    assert cache._loggat_fel is True


@pytest.mark.anyio
async def test_redis_svarscache_store_graceful_utan_ft(caplog):
    import fakeredis.aioredis as fakeredis_aio

    client = fakeredis_aio.FakeRedis(decode_responses=False)
    cache = svarscache.RedisSvarscache(client)

    post = svarscache.CachePost(
        tenant=TENANT_A,
        kbv="1",
        cfgv="1:1",
        vektor=(1.0, 0.0),
        fraga_norm="fråga",
        svar="svar",
        kategori="leverans",
    )
    with caplog.at_level("WARNING"):
        await cache.store(post)  # ska inte kasta
    assert cache._loggat_fel is True


@pytest.mark.anyio
async def test_redis_svarscache_loggar_bara_en_gang():
    import fakeredis.aioredis as fakeredis_aio

    client = fakeredis_aio.FakeRedis(decode_responses=False)
    cache = svarscache.RedisSvarscache(client)

    await cache.lookup(tenant=TENANT_A, kbv="1", cfgv="1:1", vektor=[1.0, 0.0])
    await cache.lookup(tenant=TENANT_A, kbv="1", cfgv="1:1", vektor=[1.0, 0.0])
    # Ingen assert på loggantal (caplog delas inte här) — testet bevisar
    # bara att ett andra anrop inte kraschar när flaggan redan är satt.
    assert cache._loggat_fel is True


# --- Versionering ------------------------------------------------------------


@pytest.mark.anyio
async def test_kb_version_bumpar_processlokalt_utan_redis():
    assert await versioner.kb_version(TENANT_A) == "0"
    await versioner.bumpa_kb(TENANT_A)
    assert await versioner.kb_version(TENANT_A) == "1"
    # En annan tenant påverkas inte.
    assert await versioner.kb_version(TENANT_B) == "0"


@pytest.mark.anyio
async def test_config_version_kombinerar_global_och_tenant():
    forsta = await versioner.config_version(TENANT_A)
    assert forsta == "0:0"

    await versioner.bumpa_config(TENANT_A)
    andra = await versioner.config_version(TENANT_A)
    assert andra == "0:1"
    # Annan tenant orörd av en tenant-specifik bump.
    assert await versioner.config_version(TENANT_B) == "0:0"

    await versioner.bumpa_config_global()
    tredje = await versioner.config_version(TENANT_A)
    assert tredje == "1:1"
    # Global bump träffar ÄVEN den tenant som aldrig bumpats för sig.
    assert await versioner.config_version(TENANT_B) == "1:0"


def test_tag_escapar_uuid_och_kolon():
    """Liveverifieringen 2026-08-29 föll på exakt detta: ett oescapat
    bindestreck i TAG-frågan ger "Syntax error at offset ..." hos RediSearch,
    och varje riktigt tenant-id är ett UUID med bindestreck. fakeredis kan
    inte köra FT.SEARCH, så den här rena funktionen är svitens enda vakt —
    live-beviset (träff med UUID-tenant + kolon-cfgv mot dev-databasen)
    ligger i sessionsloggen."""
    from app.cache.svarscache import RedisSvarscache

    assert (
        RedisSvarscache._tag("3f0a1b2c-4d5e-6f70-8a9b-c0d1e2f30456")
        == "3f0a1b2c\-4d5e\-6f70\-8a9b\-c0d1e2f30456"
    )
    assert RedisSvarscache._tag("3:7") == "3\:7"
    assert RedisSvarscache._tag("abc123") == "abc123"
