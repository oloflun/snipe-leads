"""Analysvyns underlag: veckoserien ska vara ÄRLIG, inte ifylld.

Vad som gick fel före den här endpointen: `/dashboard/analytics` renderade
`analyticsSeries` ur Next-appens `lib/mock-data.ts` — v16-v21, 188 skick,
21 svar, 6 möten — likadant för varje inloggad kund. Talen var påhittade och
såg kompletta ut, och en ifylld tabell blir trodd.

Testerna nedan låser de tre egenskaper som gör den nya vyn trovärdig:

  1. En vecka utan trafik finns med som en NOLLA. Grupperar man bara det som
     finns försvinner den tysta veckan ur kurvan, och en serie utan hål ser ut
     som att inget hände.
  2. Möten redovisas som `coverage: false`, aldrig som 0. Ingenting skriver
     bokade möten, och "noll möten" är ett annat påstående än "vi mäter inte
     möten".
  3. Signaturen finns i BÅDA lagringarna. Det är samma fälla som
     test_agent_run_types.py stänger för agent_runs: en metod som bara finns
     i minnet ger en grön svit mot en produktion som kastar AttributeError.
"""

from __future__ import annotations

import inspect

import pytest

from app.storage.base import ANALYTICS_COVERAGE, Storage
from app.storage.memory import MemoryStorage
from app.storage.postgres import PostgresStorage

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_signaturen_finns_i_bada_lagringarna():
    # Protokollet är källan; båda implementationerna måste matcha den.
    referens = inspect.signature(Storage.weekly_analytics)
    for lagring in (MemoryStorage, PostgresStorage):
        assert hasattr(lagring, "weekly_analytics"), (
            f"{lagring.__name__} saknar weekly_analytics. Mot den lagringen blir "
            "analysvyn en AttributeError i drift, inte i sviten."
        )
        assert inspect.signature(lagring.weekly_analytics) == referens


def test_moten_ar_otackta_inte_noll():
    # Sätts till True först den dag något faktiskt skriver bokade möten.
    assert ANALYTICS_COVERAGE["meetings"] is False


async def test_tyst_vecka_blir_en_nolla_inte_ett_hal():
    storage = MemoryStorage()

    serie = await storage.weekly_analytics("tenant-utan-trafik", weeks=6)

    assert len(serie["weeks"]) == 6, "Serien ska komma ur kalendern, inte ur raderna."
    assert all(v["sent"] == 0 for v in serie["weeks"])
    assert serie["coverage"] == ANALYTICS_COVERAGE


async def test_kornngar_raknas_per_agent_och_test_flaggas_bort():
    storage = MemoryStorage()

    async def kör(agent_type: str, *, is_test: bool = False):
        await storage.log_agent_run(
            "tenant-a",
            agent_type=agent_type,
            pack_version="v1",
            skills_used=[],
            input_text="in",
            output_text="ut",
            step_log=[],
            tokens_in=0,
            tokens_out=0,
            latency_ms=1,
            is_test=is_test,
        )

    await kör("leads")
    await kör("leads_research")
    await kör("support")
    # Adminytans provkörning är vår, inte kundens (migration 036).
    await kör("support", is_test=True)

    denna_vecka = (await storage.weekly_analytics("tenant-a", weeks=4))["weeks"][-1]

    assert denna_vecka["leads_runs"] == 2
    assert denna_vecka["support_runs"] == 1, "is_test-körningen ska inte räknas som kundvolym."


async def test_veckoantalet_klamps():
    storage = MemoryStorage()

    assert len((await storage.weekly_analytics("t", weeks=0))["weeks"]) == 1
    assert len((await storage.weekly_analytics("t", weeks=999))["weeks"]) == 52
