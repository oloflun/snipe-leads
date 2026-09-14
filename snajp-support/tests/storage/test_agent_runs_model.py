"""Migration 055 — agent_runs.model. Regression för INV-STORE-001: samma
signatur och samma skrivna värde i BÅDA lagringarna.

Bakgrund (plan §7, snipe-c9b): `agent_runs` saknade `model` helt, så två
körningar bara gick att skilja åt på filnamn — jämföraren
`scripts/jamfor_livekorningar.py` (DeepSeek mot Gemini) hade inget fält att
gruppera på. `log_agent_run` tar nu ett `model: str | None = None`-fält i
PROTOKOLLET (base.py), och skrivs av båda lagringarna.

PostgresStorage testas mot en attrapp-anslutning (samma mönster som
tests/db/test_prospect_origin_fallback.py) — det som mäts är att SQL:en och
argumentordningen faktiskt bär `model`, inte en riktig databas.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from app.storage.memory import MemoryStorage
from app.storage.postgres import PostgresStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- MemoryStorage -----------------------------------------------------------


@pytest.mark.anyio
async def test_memory_lagrar_model():
    storage = MemoryStorage()
    run = await storage.log_agent_run(
        TENANT,
        agent_type="support",
        pack_version="v1",
        skills_used=[],
        input_text="in",
        output_text="ut",
        step_log=[],
        tokens_in=0,
        tokens_out=0,
        latency_ms=1,
        model="deepseek:deepseek-v4-flash",
    )
    assert run["model"] == "deepseek:deepseek-v4-flash"

    # Hämtat i efterhand (admin-vyn) ska bära samma fält — inte bara det
    # direkt returnerade dictet.
    hamtad = await storage.get_agent_run(run["id"])
    assert hamtad is not None
    assert hamtad["model"] == "deepseek:deepseek-v4-flash"


@pytest.mark.anyio
async def test_memory_model_default_ar_none():
    """Ingen anropare ska tvingas skicka fältet — bakåtkompatibilitet för
    kodvägar som (ännu) inte är uppdaterade."""
    storage = MemoryStorage()
    run = await storage.log_agent_run(
        TENANT,
        agent_type="support",
        pack_version="v1",
        skills_used=[],
        input_text="in",
        output_text="ut",
        step_log=[],
        tokens_in=0,
        tokens_out=0,
        latency_ms=1,
    )
    assert run["model"] is None


# --- PostgresStorage (attrapp-anslutning) -------------------------------------


class _FalskConn:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.args: list[tuple] = []

    @asynccontextmanager
    async def transaction(self):
        yield

    async def fetchval(self, *args, **kwargs):
        return None

    async def fetchrow(self, query: str, *args):
        self.queries.append(" ".join(query.split()))
        self.args.append(args)
        return {"id": "11111111-1111-1111-1111-111111111111", "model": args[-1]}


class _FalskPool:
    def __init__(self, conn: _FalskConn) -> None:
        self._conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self._conn


@pytest.fixture
def lagring():
    conn = _FalskConn()
    return PostgresStorage(_FalskPool(conn)), conn


@pytest.mark.anyio
async def test_postgres_skriver_model_i_insaten(lagring):
    storage, conn = lagring

    run = await storage.log_agent_run(
        TENANT,
        agent_type="support",
        pack_version="v1",
        skills_used=[],
        input_text="in",
        output_text="ut",
        step_log=[],
        tokens_in=0,
        tokens_out=0,
        latency_ms=1,
        model="gemini:gemini-3.6-flash",
    )

    assert "model" in conn.queries[0], "INSERT-satsen saknar model-kolumnen."
    # Sista positionella argumentet i INSERT:en är model — samma ordning som
    # kolumnlistan i postgres.py.
    assert conn.args[0][-1] == "gemini:gemini-3.6-flash"
    assert run["model"] == "gemini:gemini-3.6-flash"
