"""Ändra tid för köade utkast (Anton 2026-10-10): bara de markerade
godkända flyttas, standarden för resten rörs inte."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import leads as leads_api
from app.api.schemas import SchemalaggRequest
from app.storage.memory import MemoryStorage

T = "00000000-0000-0000-0000-0000000057a1"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _post(status: str) -> dict:
    return {"id": str(uuid.uuid4()), "tenant_id": T, "thread_id": str(uuid.uuid4()),
            "status": status, "scheduled_at": datetime.now(timezone.utc), "gate_checks": {}}


@pytest.mark.anyio
async def test_bara_markerade_godkanda_flyttas():
    storage = MemoryStorage()
    vald, annan, ogodkand = _post("queued"), _post("queued"), _post("awaiting_review")
    storage.send_queue[T] = [vald, annan, ogodkand]
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(storage=storage)))
    tid = datetime.now(timezone.utc) + timedelta(days=3)
    standard = annan["scheduled_at"]

    ut = await leads_api.schemalagg_utskick(
        req, SchemalaggRequest(ids=[vald["id"], ogodkand["id"]], tid=tid), {"tenant_id": T}
    )
    assert ut["andrade"] == 1 and ut["skickas_tidigast"]
    assert vald["scheduled_at"] == tid
    assert annan["scheduled_at"] == standard and ogodkand["scheduled_at"] != tid

    with pytest.raises(HTTPException) as fel:
        await leads_api.schemalagg_utskick(
            req, SchemalaggRequest(ids=[vald["id"]], tid=datetime.now(timezone.utc) - timedelta(hours=1)),
            {"tenant_id": T},
        )
    assert fel.value.status_code == 422
