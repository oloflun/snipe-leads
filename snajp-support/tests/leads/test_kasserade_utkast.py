"""Kasserade utkast (migration 107, 2026-10-07).

Ett avvisat eller ersatt utkast blev förut kvar som osänt: det kunde väljas
som "väntande" text (ordnat på slumpmässigt uuid) och spärrade uppföljningar.
Nu kasserar en inställd köpost trådens osända utkast, och det väntande
utkastet är alltid det senaste icke-kasserade.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.leads.scheduler import avbryt_utskick_for_prospekt
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio
T = "kund-a"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _utkast(storage: MemoryStorage, trad: str, text: str) -> dict:
    return await storage.queue_outreach_message(
        T, thread_id=trad, body=text, subject="Ämne", humanizer_variant="v1",
        scheduled_at=datetime(2026, 10, 8, 8, tzinfo=timezone.utc), status="awaiting_review",
    )


async def test_senaste_utkastet_ar_det_vantande():
    storage = MemoryStorage()
    trad = (await storage.ensure_outreach_thread(T, prospect_id="p1"))["id"]
    await _utkast(storage, trad, "första")
    await _utkast(storage, trad, "andra")
    assert (await storage.get_pending_outreach_message(T, trad))["body"] == "andra"


async def test_avbrutet_utkast_kasseras_och_valjs_aldrig():
    storage = MemoryStorage()
    trad = (await storage.ensure_outreach_thread(T, prospect_id="p1"))["id"]
    await _utkast(storage, trad, "gammalt")
    assert await avbryt_utskick_for_prospekt(storage, T, "p1") == 1
    assert await storage.get_pending_outreach_message(T, trad) is None
    await _utkast(storage, trad, "nytt")
    assert (await storage.get_pending_outreach_message(T, trad))["body"] == "nytt"


async def test_prospekt_utan_trad_avbryter_ingenting():
    assert await avbryt_utskick_for_prospekt(MemoryStorage(), T, "saknas") == 0
