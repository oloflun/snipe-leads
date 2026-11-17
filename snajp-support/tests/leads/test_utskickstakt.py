"""Utskickens takt och kö (Sebbe 2026-11-16).

"100 är takt per dag, börja med de äldre utskicken. Se till att inget hamnar
i skräpposten." Dagstaket är 100 med upptrappningen kvar, kön går äldst
först, ett mejl i minuten per kund i stället för alla samma sekund 08:00, och
sändaren läser inte kön alls när inget kan gå ut. Förut prövades varje
godkänd köpost var för sig varje minut dygnet runt: 3 868 poster i main.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.leads import scheduler, send_guard
from app.leads.scheduler import TAKT_SEKUNDER, TAKT_SKAL, process_godkanda, skicka_godkant
from app.leads.send_guard import TAK_PER_DAG, Leveransutfall, TenantHistorik, dagens_tak, kundens_volymgrind
from app.storage.memory import MemoryStorage
from tests.leads.test_scheduler import OUTSIDE_WINDOW_UTC, TENANT, WITHIN_WINDOW_UTC, _FakeSendProvider, _seed

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _Klocka:
    def __init__(self, nu: datetime) -> None:
        self.nu = nu

    def now(self, tz=None):
        return self.nu


def _godkanda(storage: MemoryStorage, antal: int, *, start: datetime, svarat: bool = False) -> list[str]:
    """`antal` godkända utkast till olika bolag, köade en minut isär (äldst först)."""
    ids = []
    for i in range(antal):
        item_id, thread_id, _ = _seed(storage, scheduled_at=start + timedelta(minutes=i))
        trad = storage.outreach_threads[TENANT][thread_id]
        trad["prospect_email"] = f"vd@bolag{i}.se"
        if svarat:
            trad["last_inbound_at"] = start - timedelta(days=1)
        post = next(p for p in storage.send_queue[TENANT] if p["id"] == item_id)
        post["gate_checks"] = {"approved_by": "human", "via": "granskningskön", "godkand_i": "main"}
        ids.append(item_id)
    return ids


def _status(storage: MemoryStorage, item_id: str) -> str:
    return next(p for p in storage.send_queue[TENANT] if p["id"] == item_id)["status"]


def _historik(*, skickade_idag: int, storsta: int, alder: int = 365) -> TenantHistorik:
    return TenantHistorik(
        skickade_totalt=1000, skickade_idag=skickade_idag, tenant_alder_dagar=alder,
        storsta_dagsvolym=storsta, leverans=Leveransutfall(skickade=0, studsade=0, klagomal=0),
        senaste_kontakt_med_foretaget=None, suppressions=frozenset(),
        tidigare_kontaktade=frozenset(), egna_kunder=frozenset(),
    )


def test_taket_ar_100_och_nas_med_upptrappningen():
    assert TAK_PER_DAG == 100
    assert dagens_tak(_historik(skickade_idag=0, storsta=50)) == 55
    assert dagens_tak(_historik(skickade_idag=0, storsta=97)) == 100
    assert dagens_tak(_historik(skickade_idag=0, storsta=300)) == 100
    # Uppvärmningen är orörd.
    assert dagens_tak(_historik(skickade_idag=0, storsta=50, alder=3)) == send_guard.UPPVARMNING_TAK_PER_DAG
    assert kundens_volymgrind(_historik(skickade_idag=99, storsta=100)) is None
    beslut = kundens_volymgrind(_historik(skickade_idag=100, storsta=100))
    assert beslut is not None and beslut.regel == "5_volymtak" and "100 av 100" in beslut.skal


async def test_aldst_forst_ett_mejl_per_varv(monkeypatch):
    storage, provider = MemoryStorage(), _FakeSendProvider()
    ids = _godkanda(storage, 3, start=WITHIN_WINDOW_UTC - timedelta(days=3))

    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC))
    assert [r["outcome"] for r in await process_godkanda(storage, provider)] == ["sent"]
    assert [_status(storage, i) for i in ids] == ["sent", "queued", "queued"]

    # Samma minut: takten håller nästa.
    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC + timedelta(seconds=10)))
    assert await process_godkanda(storage, provider) == []

    # Nästa varv: näst äldsta.
    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC + timedelta(seconds=60)))
    assert [r["outcome"] for r in await process_godkanda(storage, provider)] == ["sent"]
    assert [_status(storage, i) for i in ids] == ["sent", "sent", "queued"]
    assert [m["to"] for m in provider.sent] == ["vd@bolag0.se", "vd@bolag1.se"]


async def test_utanfor_fonstret_lases_inte_kon(monkeypatch):
    storage, provider = MemoryStorage(), _FakeSendProvider()
    _godkanda(storage, 3, start=WITHIN_WINDOW_UTC - timedelta(days=3))
    lasta: list[str] = []
    original = storage.list_due_send_queue

    async def spion(tenant_id, now):
        lasta.append(tenant_id)
        return await original(tenant_id, now)

    monkeypatch.setattr(storage, "list_due_send_queue", spion)
    for nu in (
        OUTSIDE_WINDOW_UTC,  # onsdag 22:00
        datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc),  # lördag 10:00
        datetime(2026, 8, 12, 5, 30, tzinfo=timezone.utc),  # onsdag 07:30
        datetime(2026, 12, 24, 9, 0, tzinfo=timezone.utc),  # julafton
    ):
        monkeypatch.setattr(scheduler, "datetime", _Klocka(nu))
        assert await process_godkanda(storage, provider) == []
    assert lasta == [] and provider.sent == []


async def test_nadd_tak_provar_ingen_kopost(monkeypatch):
    """Taket nått: inget enskilt utkast läses eller skrivs om, varken nu
    eller nästa minut. Förut fick varje post en egen sändspärrsprövning."""
    storage, provider = MemoryStorage(), _FakeSendProvider()
    ids = _godkanda(storage, 5, start=WITHIN_WINDOW_UTC - timedelta(days=3))
    for _ in range(20):  # dagens tak för en kund utan historik är 20
        storage.outreach_messages[TENANT].append(
            {"id": f"idag-{_}", "thread_id": "historik", "direction": "outbound",
             "sent_at": WITHIN_WINDOW_UTC - timedelta(minutes=30), "body": "", "subject": ""}
        )
    upplagg: list[str] = []
    original = storage.get_outreach_thread

    async def spion(tenant_id, thread_id):
        upplagg.append(thread_id)
        return await original(tenant_id, thread_id)

    monkeypatch.setattr(storage, "get_outreach_thread", spion)
    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC))
    assert await process_godkanda(storage, provider) == []
    assert upplagg == [] and provider.sent == []
    assert all(_status(storage, i) == "queued" for i in ids)


async def test_ett_stoppat_utkast_slapper_fram_nasta(monkeypatch):
    storage, provider = MemoryStorage(), _FakeSendProvider()
    ids = _godkanda(storage, 2, start=WITHIN_WINDOW_UTC - timedelta(days=3))
    await storage.add_suppression(TENANT, email="vd@bolag0.se", reason="avregistrerad")

    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC))
    utfall = [r["outcome"] for r in await process_godkanda(storage, provider)]
    assert utfall == ["blocked", "sent"]
    assert [_status(storage, i) for i in ids] == ["blocked", "sent"]


async def test_efter_16_gar_bara_svar_i_trad(monkeypatch):
    storage, provider = MemoryStorage(), _FakeSendProvider()
    kalla = _godkanda(storage, 2, start=WITHIN_WINDOW_UTC - timedelta(days=3))
    svar = _godkanda(storage, 1, start=WITHIN_WINDOW_UTC - timedelta(days=2), svarat=True)
    storage.outreach_threads[TENANT][
        next(p for p in storage.send_queue[TENANT] if p["id"] == svar[0])["thread_id"]
    ]["prospect_email"] = "vd@svarade.se"

    halv_fem = datetime(2026, 8, 12, 14, 30, tzinfo=timezone.utc)  # 16:30 CEST
    monkeypatch.setattr(scheduler, "datetime", _Klocka(halv_fem))
    assert [r["item_id"] for r in await process_godkanda(storage, provider)] == svar
    assert [_status(storage, i) for i in kalla] == ["queued", "queued"]
    assert _status(storage, svar[0]) == "sent"


async def test_godkann_och_skicka_haller_takten():
    """Hundra godkännanden i listan blir inte hundra mejl samma minut: det
    första går, resten står kvar som godkända och tas i tur och ordning."""
    storage, provider = MemoryStorage(), _FakeSendProvider()
    ids = _godkanda(storage, 2, start=WITHIN_WINDOW_UTC - timedelta(days=3))
    for i in ids:
        next(p for p in storage.send_queue[TENANT] if p["id"] == i).update(status="awaiting_review", gate_checks={})

    assert await skicka_godkant(storage, TENANT, ids[0], provider, now=WITHIN_WINDOW_UTC) == ("sent", None)
    utfall, skal = await skicka_godkant(storage, TENANT, ids[1], provider, now=WITHIN_WINDOW_UTC + timedelta(seconds=5))
    assert (utfall, skal) == ("requeued", TAKT_SKAL)
    post = next(p for p in storage.send_queue[TENANT] if p["id"] == ids[1])
    assert post["status"] == "queued" and post["gate_checks"]["approved_by"] == "human"
    assert len(provider.sent) == 1

    # Efter takten går det med nästa varv.
    efter = WITHIN_WINDOW_UTC + timedelta(seconds=TAKT_SEKUNDER + 20)
    assert await skicka_godkant(storage, TENANT, ids[1], provider, now=efter) == ("sent", None)


async def test_skicka_nu_valjer_tiden_sjalv():
    storage, provider = MemoryStorage(), _FakeSendProvider()
    ids = _godkanda(storage, 2, start=WITHIN_WINDOW_UTC - timedelta(days=3))
    nu = WITHIN_WINDOW_UTC
    assert (await skicka_godkant(storage, TENANT, ids[0], provider, now=nu))[0] == "sent"
    assert (await skicka_godkant(storage, TENANT, ids[1], provider, now=nu, direkt=True))[0] == "sent"
