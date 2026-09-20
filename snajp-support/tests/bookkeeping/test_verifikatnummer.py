"""Verifikatnumret sätts av lagringen, atomiskt per tenant och serie.

Granskningsfynd snipe-a4y: numret räknades som `len(list_bk_verifikat())+1`
i tre API-vägar. Två samtidiga uppladdningar kunde läsa samma längd och få
SAMMA nummer — ett dubblerat verifikatnummer är en värre revisionsanmärkning
än ett hoppat. Nu skickar anroparen `nummer=None` och lagringen räknar fram
nästa lediga i serien i själva skrivningen; Postgres-vägen backas dessutom av
ett unikt index (migration 072) och försöker om vid kollision.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.storage.memory import MemoryStorage

TENANT_A = "00000000-0000-4000-a000-00000000000a"
TENANT_B = "00000000-0000-4000-a000-00000000000b"

RADER = [
    {"konto": "1930", "kredit": Decimal("125.00"), "text": ""},
    {"konto": "4010", "debet": Decimal("100.00"), "text": ""},
    {"konto": "2641", "debet": Decimal("25.00"), "text": ""},
]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _skapa(storage, tenant, *, serie="A", nummer=None):
    return await storage.create_bk_verifikat(
        tenant,
        underlag_id="00000000-0000-4000-b000-000000000001",
        serie=serie,
        nummer=nummer,
        datum=date(2026, 3, 5),
        text="test",
        rader=RADER,
    )


@pytest.mark.anyio
async def test_nummer_none_ger_lopande_serie():
    storage = MemoryStorage()
    forsta = await _skapa(storage, TENANT_A)
    andra = await _skapa(storage, TENANT_A)
    tredje = await _skapa(storage, TENANT_A)
    assert [forsta["nummer"], andra["nummer"], tredje["nummer"]] == ["1", "2", "3"]


@pytest.mark.anyio
async def test_serien_ar_per_tenant():
    storage = MemoryStorage()
    await _skapa(storage, TENANT_A)
    await _skapa(storage, TENANT_A)
    forsta_b = await _skapa(storage, TENANT_B)
    assert forsta_b["nummer"] == "1"


@pytest.mark.anyio
async def test_serien_ar_per_serie():
    storage = MemoryStorage()
    await _skapa(storage, TENANT_A, serie="A")
    forsta_b = await _skapa(storage, TENANT_A, serie="B")
    assert forsta_b["nummer"] == "1"


@pytest.mark.anyio
async def test_explicit_nummer_respekteras():
    """SIE-import och tester som sätter numret själva ska inte ändras."""
    storage = MemoryStorage()
    post = await _skapa(storage, TENANT_A, nummer="17")
    assert post["nummer"] == "17"
    # Nästa automatiska nummer fortsätter EFTER det explicita, inte i ett
    # parallellt spår — två nummerkällor får aldrig ge samma värde.
    nasta = await _skapa(storage, TENANT_A)
    assert nasta["nummer"] == "18"
