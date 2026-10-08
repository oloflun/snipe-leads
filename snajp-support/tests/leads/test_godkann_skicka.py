"""Godkänn och skicka (2026-10-07).

Knappen satte förut bara status 'queued', och eftersom ingen schemaläggare
körde skickades ingenting. Nu skickar den just det godkända utkastet direkt,
genom samma grindar som schemaläggaren, och väntar annars på sändfönstret.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.leads import scheduler
from app.leads.scheduler import process_godkanda, skicka_godkant
from app.storage.memory import MemoryStorage
from tests.leads.test_scheduler import (
    GODKAND_BRODTEXT,
    OUTSIDE_WINDOW_UTC,
    TENANT,
    WITHIN_WINDOW_UTC,
    _FakeSendProvider,
    _seed,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _ny_kund(storage: MemoryStorage, **k) -> tuple[str, str, str]:
    """Ett utkast i granskningskön hos en kund som aldrig skickat något:
    regel 6 hade hållit kvar det, och autonominivån är 'draft'."""
    ids = _seed(storage, autonomy="draft", **k)
    storage.outreach_messages[TENANT] = [m for m in storage.outreach_messages[TENANT] if m["thread_id"] != "historik"]
    storage.send_queue[TENANT][-1]["status"] = "awaiting_review"
    return ids


def _post(storage: MemoryStorage, item_id: str) -> dict:
    return next(i for i in storage.send_queue[TENANT] if i["id"] == item_id)


class _Klocka:
    def __init__(self, nu: datetime) -> None:
        self.nu = nu

    def now(self, tz=None):
        return self.nu


async def test_godkant_inom_fonstret_skickas_direkt():
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    utfall, skal = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)
    assert (utfall, skal) == ("sent", None)
    assert provider.sent and provider.sent[0]["body"] == GODKAND_BRODTEXT
    assert _post(storage, item_id)["status"] == "sent"


async def test_redigerad_text_ar_den_som_skickas():
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, thread_id, message_id = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    ny = GODKAND_BRODTEXT.replace("jag såg en signal", "vi såg er nya lokal")
    await storage.update_outreach_message_text(TENANT, message_id, subject="Ny lokal", body=ny)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)
    assert provider.sent[0]["subject"] == "Ny lokal" and "er nya lokal" in provider.sent[0]["body"]


async def test_utanfor_fonstret_vantar_det_godkant_och_gar_ut_nar_fonstret_oppnar(monkeypatch):
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, _, _ = _ny_kund(storage, scheduled_at=OUTSIDE_WINDOW_UTC)
    utfall, _ = await skicka_godkant(storage, TENANT, item_id, provider, now=OUTSIDE_WINDOW_UTC)
    assert utfall == "requeued" and provider.sent == []
    post = _post(storage, item_id)
    assert post["status"] == "queued" and post["gate_checks"]["approved_by"] == "human"

    nasta_morgon = OUTSIDE_WINDOW_UTC + timedelta(hours=12)  # torsdag 10:00 lokal tid
    monkeypatch.setattr(scheduler, "datetime", _Klocka(nasta_morgon))
    resultat = await process_godkanda(storage, provider)
    assert [r["outcome"] for r in resultat] == ["sent"]
    assert _post(storage, item_id)["status"] == "sent"


async def test_sandaren_ror_aldrig_ett_autonomt_koat_utkast(monkeypatch):
    storage, provider = MemoryStorage(), _FakeSendProvider()
    _seed(storage, scheduled_at=WITHIN_WINDOW_UTC, autonomy="meeting")  # 'queued', inget godkännande
    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC))
    assert await process_godkanda(storage, provider) == []
    assert provider.sent == []


async def test_spegeln_skickar_inte_ett_godkannande_fran_produktionen(monkeypatch):
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, _, _ = _ny_kund(storage, scheduled_at=OUTSIDE_WINDOW_UTC)
    await skicka_godkant(storage, TENANT, item_id, provider, now=OUTSIDE_WINDOW_UTC)

    async def spegel():
        return {"environment": "development", "seeded_at": (OUTSIDE_WINDOW_UTC + timedelta(hours=1)).isoformat()}

    monkeypatch.setattr(storage, "spegel_info", spegel)
    monkeypatch.setattr(scheduler, "datetime", _Klocka(OUTSIDE_WINDOW_UTC + timedelta(hours=12)))
    assert await process_godkanda(storage, provider) == []
    assert provider.sent == []


@pytest.mark.parametrize(
    ("skapad_efter_speglingen", "skickas"),
    [(True, True), (False, False)],
)
async def test_spegeln_skickar_ett_aldre_godkannande_bara_om_posten_ar_spegelns_egen(
    monkeypatch, skapad_efter_speglingen, skickas
):
    """Godkännanden före 2026-10-07 saknar godkand_at. En köpost skapad efter
    speglingen finns inte i produktionen och ska skickas; en kopierad ska inte."""
    storage, provider = MemoryStorage(), _FakeSendProvider()
    seedad = OUTSIDE_WINDOW_UTC
    item_id, _, _ = _ny_kund(storage, scheduled_at=OUTSIDE_WINDOW_UTC)
    post = _post(storage, item_id)
    post.update(
        status="queued",
        gate_checks={"approved_by": "human", "via": "granskningskön"},
        created_at=seedad + timedelta(hours=1 if skapad_efter_speglingen else -1),
    )

    async def spegel():
        return {"environment": "development", "seeded_at": seedad.isoformat()}

    monkeypatch.setattr(storage, "spegel_info", spegel)
    monkeypatch.setattr(scheduler, "datetime", _Klocka(OUTSIDE_WINDOW_UTC + timedelta(hours=12)))
    resultat = await process_godkanda(storage, provider)
    assert [r["outcome"] for r in resultat] == (["sent"] if skickas else [])
    assert bool(provider.sent) is skickas


async def test_ovriga_sparrar_galler_aven_godkant():
    storage, provider = MemoryStorage(), _FakeSendProvider()
    utan_lank = GODKAND_BRODTEXT.replace("Avregistrera dig: https://testbolaget.example/avregistrera?t=abc\n", "")
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC, body=utan_lank)
    utfall, skal = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)
    assert utfall == "blocked" and skal and provider.sent == []


async def test_ett_hanterat_utkast_skickas_inte_igen():
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)
    assert (await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC))[0] == "redan_hanterad"
    assert len(provider.sent) == 1
