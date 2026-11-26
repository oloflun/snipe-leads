"""Mot en riktig Postgres, som approllen snajp_app (Codex-granskningen 2026-11-19):

* `lagg_till_kb_forslag` skriver artikeln och beslutet i EN transaktion. Ett
  fel mitt i (här: en inbäddning som inte går att skicka) lämnar utkastet
  väntande och ingen artikel, och ett nytt försök lyckas.
* Migration 130 lägger tillbaka utkast som den gamla koden lämnade som
  `tillagd` utan artikel.
* Migration 129: approllen läser migrationsliggaren (`schema_versioner`).

Körs i CI-jobbet `databas` (.github/workflows/verify.yml). Vägrar allt annat än
en lokal databas utan spegelmarkör. Kunden och utkasten är syntetiska och
raderas efteråt.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
APP_DSN = os.environ.get("GALLRING_TEST_APP_DSN", "")
_LOKALA = {"localhost", "127.0.0.1", "::1"}
MIGRATION_130 = (
    Path(__file__).resolve().parents[3] / "db" / "migrations" / "20261119100000_130_kb_forslag_utan_artikel.sql"
)

pytestmark = pytest.mark.skipif(
    not (DSN and APP_DSN),
    reason="Kräver GALLRING_TEST_DSN och GALLRING_TEST_APP_DSN mot en tom testdatabas.",
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _agare() -> asyncpg.Connection:
    assert urlsplit(DSN).hostname in _LOKALA, "Testet körs bara mot en lokal databas."
    conn = await asyncpg.connect(DSN)
    assert not await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    return conn


async def _kund_med_utkast(agare: asyncpg.Connection, status: str = "vantar") -> tuple[str, str]:
    tid = uuid.uuid4()
    await agare.execute(
        "insert into ss_tenants (id, slug, name) values ($1, $2, 'KB-test')", tid, f"kb-{tid.hex[:12]}"
    )
    skanning = await agare.fetchval(
        "insert into ss_kb_skanningar (tenant_id, webbplats, status) values ($1, 'exempel.se', 'klar') returning id",
        str(tid),
    )
    forslag = await agare.fetchval(
        """
        insert into ss_kb_forslag (tenant_id, skanning_id, title, content, category, status)
        values ($1, $2, 'Retur och byte', 'Trettio dagars öppet köp.', 'ovrigt', $3) returning id
        """,
        str(tid), skanning, status,
    )
    return str(tid), str(forslag)


async def _stada(agare: asyncpg.Connection, tid: str) -> None:
    await agare.execute("delete from ss_kb_forslag where tenant_id = $1", tid)
    await agare.execute("delete from ss_kb_skanningar where tenant_id = $1", tid)
    await agare.execute("delete from ss_knowledge_base where tenant_id = $1", tid)
    await agare.execute("delete from ss_tenants where id = $1::uuid", tid)


@pytest.mark.anyio
async def test_ett_fel_mitt_i_rullar_tillbaka_och_ett_nytt_forsok_lyckas():
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    tid, fid = await _kund_med_utkast(agare)
    pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
    try:
        lager = PostgresStorage(pool)
        with pytest.raises(Exception):
            # Inbäddningen kan inte skickas utan vektorkodek: felet kommer
            # efter radlåset, mitt i transaktionen.
            await lager.lagg_till_kb_forslag(tid, fid, embedding=[0.1, 0.2])
        assert await agare.fetchval("select status from ss_kb_forslag where id = $1::uuid", fid) == "vantar"
        assert await agare.fetchval("select count(*) from ss_knowledge_base where tenant_id = $1", tid) == 0
        assert (await lager.hamta_vantande_kb_forslag(tid, fid))["title"] == "Retur och byte"

        artikel = await lager.lagg_till_kb_forslag(tid, fid, embedding=None)
        assert artikel and artikel["title"] == "Retur och byte"
        rad = await agare.fetchrow("select status, artikel_id from ss_kb_forslag where id = $1::uuid", fid)
        assert rad["status"] == "tillagd" and str(rad["artikel_id"]) == str(artikel["id"])
        # Ett andra klick blir ingen andra artikel.
        assert await lager.lagg_till_kb_forslag(tid, fid, embedding=None) is None
        assert await agare.fetchval("select count(*) from ss_knowledge_base where tenant_id = $1", tid) == 1
    finally:
        await pool.close()
        await _stada(agare, tid)
        await agare.close()


@pytest.mark.anyio
async def test_kb_versionen_foljer_artikelns_transaktion():
    """Migration 137 (Codex runda 6): svarscachens KB-version byter värde i
    samma transaktion som artikeln, inte efteråt i Redis. En tillbakarullad
    skrivning lämnar den orörd, en lyckad byter den, en annan kund ser den
    inte, och raden följer kunden när kunden raderas."""
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    tid, fid = await _kund_med_utkast(agare)
    annan, _ = await _kund_med_utkast(agare)
    pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
    try:
        lager = PostgresStorage(pool)
        fore, _ = await lager.kb_cachestatus(tid)
        assert fore == "0"

        with pytest.raises(Exception):
            await lager.lagg_till_kb_forslag(tid, fid, embedding=[0.1, 0.2])
        assert (await lager.kb_cachestatus(tid))[0] == fore, "en tillbakarullad skrivning höjde versionen"

        assert await lager.lagg_till_kb_forslag(tid, fid, embedding=None)
        efter, _ = await lager.kb_cachestatus(tid)
        assert efter != fore, "artikeln committades utan att KB-versionen bytte värde"
        assert (await lager.kb_cachestatus(annan))[0] == "0", "en annan kunds version påverkades"

        # Radskyddet: approllen med en annan kunds tenant ser inte raden.
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("select set_config('app.tenant_id', $1, true)", annan)
                assert await conn.fetchval("select count(*) from ss_kb_version where tenant_id = $1::uuid", tid) == 0
    finally:
        await pool.close()
        await _stada(agare, tid)
        await _stada(agare, annan)
        rester = await agare.fetchval(
            "select count(*) from ss_kb_version where tenant_id = any($1::uuid[])", [tid, annan])
        await agare.close()
    assert rester == 0, "KB-versionen blev kvar efter att kunden raderats"


@pytest.mark.anyio
async def test_migration_130_lagger_tillbaka_utkast_utan_artikel():
    agare = await _agare()
    tid, fid = await _kund_med_utkast(agare, status="tillagd")
    try:
        sql = MIGRATION_130.read_text(encoding="utf-8")
        for _ in range(2):  # idempotent
            await agare.execute(sql)
        rad = await agare.fetchrow("select status, beslutad_at from ss_kb_forslag where id = $1::uuid", fid)
        assert rad["status"] == "vantar" and rad["beslutad_at"] is None
    finally:
        await _stada(agare, tid)
        await agare.close()


@pytest.mark.anyio
async def test_approllen_laser_migrationsliggaren():
    from app.storage.postgres import PostgresStorage

    pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
    try:
        versioner = await PostgresStorage(pool).schema_versioner()
    finally:
        await pool.close()
    assert "20261119090000_129_schema_lasvag" in versioner
