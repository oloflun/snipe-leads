"""Bakgrundskön (Del J): process_due_item är den ENDA kodvägen som får
sätta status='sent' — grindarna körs igen här, inte bara vid köning."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.leads.scheduler import process_all_due, process_due_item
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeSendProvider:
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


def _seed(storage: MemoryStorage, *, scheduled_at, language_state="sv", humanizer_variant="snajp:humanizer-svenska", last_inbound_at=None):
    thread_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    item_id = str(uuid.uuid4())

    storage.outreach_threads.setdefault(TENANT, {})[thread_id] = {
        "id": thread_id,
        "language_state": language_state,
        "last_inbound_at": last_inbound_at,
        "prospect_email": "prospect@example.se",
    }
    storage.outreach_messages.setdefault(TENANT, []).append(
        {
            "id": message_id,
            "thread_id": thread_id,
            "direction": "outbound",
            "sent_at": None,
            "body": "Hej, jag såg en signal som gör tajmingen relevant.",
            "subject": "En idé till er",
            "humanizer_variant": humanizer_variant,
        }
    )
    storage.send_queue.setdefault(TENANT, []).append(
        {
            "id": item_id,
            "thread_id": thread_id,
            "scheduled_at": scheduled_at,
            "status": "queued",
            "gate_checks": {},
        }
    )
    return item_id, thread_id, message_id


# En onsdag inom kallt-utskick-fönstret respektive utanför det, i UTC (för
# att matcha datetime.now(timezone.utc) i scheduler.py).
WITHIN_WINDOW_UTC = datetime(2026, 8, 12, 8, 0, tzinfo=timezone.utc)  # 10:00 CEST
OUTSIDE_WINDOW_UTC = datetime(2026, 8, 12, 20, 0, tzinfo=timezone.utc)  # 22:00 CEST


@pytest.mark.anyio
async def test_sends_and_marks_message_and_queue_item_when_gates_pass(monkeypatch):
    storage = MemoryStorage()
    item_id, thread_id, message_id = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    provider = _FakeSendProvider()

    outcome = await process_due_item(storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC)

    assert outcome == "sent"
    assert provider.sent == [
        {
            "to": "prospect@example.se",
            "subject": "En idé till er",
            "body": "Hej, jag såg en signal som gör tajmingen relevant.",
        }
    ]
    message = next(m for m in storage.outreach_messages[TENANT] if m["id"] == message_id)
    assert message["sent_at"] == WITHIN_WINDOW_UTC
    queue_item = next(i for i in storage.send_queue[TENANT] if i["id"] == item_id)
    assert queue_item["status"] == "sent"


@pytest.mark.anyio
async def test_requeues_without_sending_when_outside_window():
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(storage, scheduled_at=OUTSIDE_WINDOW_UTC)
    provider = _FakeSendProvider()

    outcome = await process_due_item(storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=OUTSIDE_WINDOW_UTC)

    assert outcome == "requeued"
    assert provider.sent == []
    queue_item = next(i for i in storage.send_queue[TENANT] if i["id"] == item_id)
    assert queue_item["status"] == "queued"  # inte 'blocked' — bara utanför fönstret just nu


@pytest.mark.anyio
async def test_blocks_on_language_mismatch_without_sending():
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(
        storage,
        scheduled_at=WITHIN_WINDOW_UTC,
        language_state="en_confirmed",
        humanizer_variant="snajp:humanizer-svenska",  # fel variant
    )
    provider = _FakeSendProvider()

    outcome = await process_due_item(storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC)

    assert outcome == "blocked"
    assert provider.sent == []
    queue_item = next(i for i in storage.send_queue[TENANT] if i["id"] == item_id)
    assert queue_item["status"] == "blocked"


@pytest.mark.anyio
async def test_process_all_due_skips_items_not_yet_due():
    storage = MemoryStorage()
    await storage.create_tenant(slug="tenant-a", name="Tenant A")
    # create_tenant genererar ett nytt id — vi seedar med tenant["id"] i stället för TENANT-strängen.
    tenants = await storage.list_tenants()
    tenant_id = tenants[0]["id"]

    # Relativt till verklig väggklocka (inte de fasta 2026-08-12-tiderna ovan)
    # så testet förblir korrekt oavsett vilket år det faktiskt körs.
    future = datetime.now(timezone.utc) + timedelta(days=1)
    thread_id = str(uuid.uuid4())
    storage.outreach_threads.setdefault(tenant_id, {})[thread_id] = {
        "id": thread_id, "language_state": "sv", "last_inbound_at": None, "prospect_email": "x@example.se"
    }
    storage.send_queue.setdefault(tenant_id, []).append(
        {"id": "item-1", "thread_id": thread_id, "scheduled_at": future, "status": "queued", "gate_checks": {}}
    )

    provider = _FakeSendProvider()
    results = await process_all_due(storage, provider)
    assert results == []  # inget är due än
