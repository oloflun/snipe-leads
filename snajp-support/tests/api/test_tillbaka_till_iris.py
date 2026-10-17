"""Tillbaka till Iris (Anton 2026-10-10, ändrat 2026-10-12): markerade utkast i
sändlistan avbryts och leadsen står som nya hos Iris. Inget skrivs om
automatiskt, och inget tak på antalet."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api import leads as leads_api
from app.api.schemas import TillbakaTillIrisRequest
from app.storage.memory import MemoryStorage

T = "00000000-0000-0000-0000-0000000057a2"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _lead(storage: MemoryStorage, status: str) -> dict:
    prospekt = {"id": str(uuid.uuid4()), "tenant_id": T, "company_name": f"Bolag {status}", "status": "new"}
    trad = {"id": str(uuid.uuid4()), "tenant_id": T, "prospect_id": prospekt["id"]}
    post = {"id": str(uuid.uuid4()), "tenant_id": T, "thread_id": trad["id"], "status": status,
            "scheduled_at": datetime.now(timezone.utc), "gate_checks": {}}
    storage.prospects.setdefault(T, []).append(prospekt)
    storage.outreach_threads.setdefault(T, {})[trad["id"]] = trad
    storage.send_queue.setdefault(T, []).append(post)
    return post


@pytest.mark.anyio
async def test_markerade_avbryts_utan_omskrivning(monkeypatch):
    storage = MemoryStorage()
    koad, granskas, skickad, annan = (_lead(storage, s) for s in ("queued", "awaiting_review", "sent", "queued"))

    async def _lagg(*_a, **_k):  # pragma: no cover - ska aldrig anropas
        raise AssertionError("Tillbaka till Iris får inte köa någon omskrivning")

    monkeypatch.setattr(leads_api, "_lagg_prospektjobb", _lagg)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(storage=storage)))

    ut = await leads_api.tillbaka_till_iris(
        req, TillbakaTillIrisRequest(ids=[koad["id"], granskas["id"], skickad["id"]]), {"tenant_id": T}
    )
    assert ut == {"count": 2, "jobs": []}
    assert koad["status"] == "cancelled" and granskas["status"] == "cancelled"
    # Ett skickat utkast och ett omarkerat rörs inte.
    assert skickad["status"] == "sent" and annan["status"] == "queued"


def test_inget_tak_pa_antalet():
    assert len(TillbakaTillIrisRequest(ids=[str(uuid.uuid4()) for _ in range(600)]).ids) == 600
