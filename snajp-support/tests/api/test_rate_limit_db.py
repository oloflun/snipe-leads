"""Taken i migration 019: räknade i LLM-anrop, delade mellan processer,
och fail-open när mätningen själv är trasig.

Testar mot MemoryStorage, som implementerar samma två metoder som
PostgresStorage. Det är medvetet: det var precis genom att MemoryStorage
saknade Postgres check-villkor som agent_runs.agent_type-buggen kunde gömma
sig i ett halvår. Metoderna finns nu i BÅDA, och det här testet kör den ena.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.api import rate_limit_db
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def storage():
    return MemoryStorage()


async def test_under_taket_slapper_igenom(storage):
    scopes = rate_limit_db.scopes_for("tenant-a", "user-1")
    await rate_limit_db.record(storage, scopes, 10)
    await rate_limit_db.enforce(storage, scopes)  # ska inte kasta


async def test_tenant_taket_stoppar_vid_gransen(storage):
    scopes = rate_limit_db.scopes_for("tenant-a", None)
    await rate_limit_db.record(storage, scopes, rate_limit_db.TENANT_HOURLY_LLM_CALLS)

    with pytest.raises(rate_limit_db.RateLimitDbExceededError) as caught:
        await rate_limit_db.enforce(storage, scopes)

    assert caught.value.scope_kind == "tenant"
    assert caught.value.cap == rate_limit_db.TENANT_HOURLY_LLM_CALLS


async def test_anvandartaket_slar_fore_tenanttaket(storage):
    """Ett kapat konto ska stoppas långt innan det bränner tenantens kvot."""
    scopes = rate_limit_db.scopes_for("tenant-a", "user-1")
    await rate_limit_db.record(storage, scopes, rate_limit_db.USER_HOURLY_LLM_CALLS)

    with pytest.raises(rate_limit_db.RateLimitDbExceededError) as caught:
        await rate_limit_db.enforce(storage, scopes)

    assert caught.value.scope_kind == "user"


async def test_en_annan_anvandare_i_samma_tenant_pavarkas_inte(storage):
    """Kvoten per person får inte bli en funktion av kollegans flit."""
    await rate_limit_db.record(
        storage,
        rate_limit_db.scopes_for(None, "user-1"),
        rate_limit_db.USER_HOURLY_LLM_CALLS,
    )
    await rate_limit_db.enforce(storage, rate_limit_db.scopes_for(None, "user-2"))


async def test_taket_ar_ett_glidande_timfonster(storage):
    scopes = rate_limit_db.scopes_for("tenant-a", None)
    await rate_limit_db.record(storage, scopes, rate_limit_db.TENANT_HOURLY_LLM_CALLS)

    # Två timmar senare är samma händelser utanför fönstret.
    framtiden = datetime.now(timezone.utc) + timedelta(hours=2)
    await rate_limit_db.enforce(storage, scopes, now=framtiden)


async def test_demons_ip_tak_ar_skilt_fran_kundernas(storage):
    """Demon räknas i svar och på ett eget scope. Ett fullt IP-tak får aldrig
    stoppa en inloggad, betalande kund."""
    ip = rate_limit_db.demo_ip_scope("203.0.113.7")
    await rate_limit_db.record(storage, ip, rate_limit_db.DEMO_IP_HOURLY_RESPONSES)

    with pytest.raises(rate_limit_db.RateLimitDbExceededError):
        await rate_limit_db.enforce(storage, ip)

    await rate_limit_db.enforce(storage, rate_limit_db.scopes_for("tenant-a", "user-1"))


async def test_fail_open_nar_uppslaget_kraschar(storage):
    """En trasig mätning får inte bli ett avbrott för en betalande kund."""

    class TrasigLagring:
        async def count_rate_events(self, **_):
            raise RuntimeError("anslutningen dog mitt i uppslaget")

        async def record_rate_events(self, **_):
            raise RuntimeError("samma sak på vägen ut")

    trasig = TrasigLagring()
    scopes = rate_limit_db.scopes_for("tenant-a", "user-1")

    await rate_limit_db.enforce(trasig, scopes)  # släpper igenom
    await rate_limit_db.record(trasig, scopes, 6)  # sväljer felet


async def test_noll_anrop_bokfors_inte(storage):
    """En körning som inte gjorde några LLM-anrop ska inte kosta kvot."""
    scopes = rate_limit_db.scopes_for("tenant-a", None)
    await rate_limit_db.record(storage, scopes, 0)
    assert (
        await storage.count_rate_events(
            scope_kind="tenant",
            scope_id="tenant-a",
            kind=rate_limit_db.LLM_CALL,
            since=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        == 0
    )
