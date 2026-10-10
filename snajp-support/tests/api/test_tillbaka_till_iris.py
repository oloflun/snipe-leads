"""Tillbaka till Iris (Anton 2026-10-10): markerade utkast i sändlistan avbryts
och bolagen skrivs om genom samma kedja som körningens "Skriv utkast"."""

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
async def test_markerade_avbryts_och_skrivs_om(monkeypatch):
    storage = MemoryStorage()
    koad, granskas, skickad, annan = (_lead(storage, s) for s in ("queued", "awaiting_review", "sent", "queued"))
    jobb: list[list[str]] = []

    async def _lagg(_state, _tenant, prospekt, *, scope, **_k):
        assert scope == "research_and_draft"
        jobb.append([p["company_name"] for p in prospekt])
        return [{"job_id": str(uuid.uuid4())} for _ in prospekt]

    async def _budget(*_a, **_k):
        return None

    monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
    monkeypatch.setattr(leads_api, "_kraev_leads_budget", _budget)
    monkeypatch.setattr(leads_api, "_lagg_prospektjobb", _lagg)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(storage=storage)))

    ut = await leads_api.tillbaka_till_iris(
        req, TillbakaTillIrisRequest(ids=[koad["id"], granskas["id"], skickad["id"]]), {"tenant_id": T}
    )
    assert ut["count"] == 2
    assert jobb == [["Bolag queued", "Bolag awaiting_review"]]
    assert koad["status"] == "cancelled" and granskas["status"] == "cancelled"
    # Ett skickat utkast och ett omarkerat rörs inte.
    assert skickad["status"] == "sent" and annan["status"] == "queued"
