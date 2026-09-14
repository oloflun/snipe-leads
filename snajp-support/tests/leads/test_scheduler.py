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


#: En brödtext som passerar send_guard regel 1 och 2 (avsändaridentifikation
#: och avregistreringslänk). Testerna i den här filen mäter SCHEMALÄGGAREN, så
#: de behöver ett mejl som spärrarna släpper igenom — annars hade de mätt
#: send_guard i stället, och den har sina egna tester i test_send_guard.py.
GODKAND_BRODTEXT = """Hej, jag såg en signal som gör tajmingen relevant.

Testbolaget AB · Org.nr 556000-0000 · Testgatan 1, 111 22 Stockholm
Avregistrera dig: https://testbolaget.example/avregistrera?t=abc
"""


def _seed(storage: MemoryStorage, *, scheduled_at, language_state="sv", humanizer_variant="snajp:humanizer-svenska", last_inbound_at=None, autonomy="first_contact", body=GODKAND_BRODTEXT):
    # autonomy default 'first_contact' här, inte 'draft': testerna nedan mäter
    # SÄNDNINGSVÄGEN, och med produktionsdefaulten 'draft' hade de mätt
    # autonomigrinden i stället. Draft-beteendet har egna tester längst ned.
    storage.agent_settings[(TENANT, "leads")] = {"autonomy": autonomy}
    # send_guard regel 1 läser avsändaridentiteten ur tenanten, och regel 6
    # kräver att de tre första utskicken redan är gjorda för att inte tvinga
    # allt till granskning.
    storage.tenants[TENANT] = {
        "id": TENANT,
        "name": "Testbolaget AB",
        "company_name": "Testbolaget AB",
        "orgnr": "556000-0000",
        "postal_address": "Testgatan 1, 111 22 Stockholm",
        "created_at": scheduled_at - timedelta(days=365),
    }
    for _ in range(3):
        storage.outreach_messages.setdefault(TENANT, []).append(
            {
                "id": str(uuid.uuid4()),
                "thread_id": "historik",
                "direction": "outbound",
                "sent_at": scheduled_at - timedelta(days=200),
                "body": "",
                "subject": "",
                "humanizer_variant": humanizer_variant,
            }
        )
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
            "body": body,
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
            "body": GODKAND_BRODTEXT,
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


# -- Autonominivån (Fas 4.1) -------------------------------------------------
#
# Grinden sitter på BÅDA ställena: vid köningen och här. Ett item kan ha köats
# innan kunden sänkte sin nivå, och då ska det stoppas — inte skickas för att
# det hann godkännas av en regel som gällde igår.


@pytest.mark.anyio
async def test_draft_haller_kvar_aven_ett_koat_item():
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC, autonomy="draft")
    provider = _FakeSendProvider()

    outcome = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert outcome == "awaiting_review"
    assert provider.sent == []
    assert storage.send_queue[TENANT][0]["status"] == "awaiting_review"


@pytest.mark.anyio
async def test_first_contact_skickar_forsta_men_haller_uppfoljningen():
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(
        storage, scheduled_at=WITHIN_WINDOW_UTC, autonomy="first_contact"
    )
    provider = _FakeSendProvider()

    first = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )
    assert first == "sent"

    # Uppföljning i samma tråd: ett skickat meddelande finns nu, alltså
    # sequence_index 1, som first_contact inte tillåter.
    follow_up_id = str(uuid.uuid4())
    storage.outreach_messages[TENANT].append(
        {
            "id": follow_up_id,
            "thread_id": thread_id,
            "direction": "outbound",
            "sent_at": None,
            "body": "Hör bara av mig igen.",
            "subject": "Uppföljning",
            "humanizer_variant": "snajp:humanizer-svenska",
        }
    )
    second_item_id = str(uuid.uuid4())
    storage.send_queue[TENANT].append(
        {
            "id": second_item_id,
            "thread_id": thread_id,
            "scheduled_at": WITHIN_WINDOW_UTC,
            "status": "queued",
            "gate_checks": {},
        }
    )

    second = await process_due_item(
        storage,
        TENANT,
        {"id": second_item_id, "thread_id": thread_id},
        provider,
        now=WITHIN_WINDOW_UTC,
    )
    assert second == "awaiting_review"
    assert len(provider.sent) == 1


# -- send_guard sitter i sändvägen (DEL 2.3) -------------------------------
#
# De sex reglerna har sina egna tester i test_send_guard.py. Testerna nedan
# bevisar något annat och lika viktigt: att schemaläggaren faktiskt ANROPAR
# dem. En spärr som ingen anropar är dekoration.


@pytest.mark.anyio
async def test_send_guard_blockerar_mejl_utan_avregistreringslank():
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(
        storage,
        scheduled_at=WITHIN_WINDOW_UTC,
        body="Hej! Köp något.\n\nTestbolaget AB · Org.nr 556000-0000 · Testgatan 1, 111 22 Stockholm",
    )
    provider = _FakeSendProvider()

    outcome = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert outcome == "blocked"
    assert provider.sent == []
    item = storage.send_queue[TENANT][0]
    assert item["gate_checks"]["send_guard_regel"] == "2_avregistrering"


@pytest.mark.anyio
async def test_send_guard_blockerar_avregistrerad_mottagare():
    """Avregistreringen kan ha skett MEDAN utkastet låg i kön. Det är hela
    skälet till att kontrollen sker i sändningsögonblicket."""
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    await storage.add_suppression(TENANT, email="Prospect@Example.se", reason="klickade avregistrera")
    provider = _FakeSendProvider()

    outcome = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert outcome == "blocked"
    assert provider.sent == []
    assert storage.send_queue[TENANT][0]["gate_checks"]["send_guard_regel"] == "3_suppression"


@pytest.mark.anyio
async def test_send_guard_lagger_de_tre_forsta_i_granskning():
    """Regel 6 gäller oavsett autonominivå — här är den first_contact."""
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    storage.outreach_messages[TENANT] = [
        m for m in storage.outreach_messages[TENANT] if m["thread_id"] != "historik"
    ]
    provider = _FakeSendProvider()

    outcome = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert outcome == "awaiting_review"
    assert provider.sent == []
    assert storage.send_queue[TENANT][0]["gate_checks"]["send_guard_regel"] == "6_granskningsko"


@pytest.mark.anyio
async def test_avregistrering_ar_idempotent():
    storage = MemoryStorage()
    await storage.add_suppression(TENANT, email="a@b.se", reason="första")
    await storage.add_suppression(TENANT, email="A@B.se", reason="andra")
    assert await storage.list_suppressions(TENANT) == {"a@b.se"}


@pytest.mark.anyio
async def test_exempelbolag_kan_aldrig_mejlas_sparr_noll():
    """Spärr noll: ett påhittat bolag lämnar aldrig huset.

    Kontrollen sitter i sändningsvägen och inte i UI:t, av samma skäl som de
    sex reglerna gör det — det här är den enda punkt varje utskick måste
    passera. Ett påhittat bolagsnamn kan råka vara ett RIKTIGT bolag; då är
    mejlet inte ofarligt, det är fel mottagare.

    Allt annat i den här körningen är godkänt: rätt fönster, godkänd brödtext,
    autonominivå som tillåter utskick. Det är avsiktligt — faller det ändå är
    det ursprungsmarkeringen som fällde det, ingenting annat.
    """
    storage = MemoryStorage()
    item_id, thread_id, message_id = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    provider = _FakeSendProvider()

    exempel = await storage.create_prospect(
        TENANT, company_name="Nordvik Bygg AB", origin="example"
    )
    storage.outreach_threads[TENANT][thread_id]["prospect_id"] = exempel["id"]

    outcome = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert outcome == "blocked"
    assert provider.sent == []
    queue_item = next(i for i in storage.send_queue[TENANT] if i["id"] == item_id)
    assert queue_item["status"] == "blocked"
    assert "exempelbolag" in str(queue_item["gate_checks"]).lower()
    # Meddelandet får inte heller märkas som skickat — en 'sent_at' på ett
    # blockerat utskick hade fått historiken att räkna det som levererat.
    message = next(m for m in storage.outreach_messages[TENANT] if m["id"] == message_id)
    assert message["sent_at"] is None


@pytest.mark.anyio
async def test_test_ursprung_kan_aldrig_mejlas_sparr_noll():
    """Samma spärr noll som exempelbolag, för migration 054:s 'test'-origin.

    Ett prospekt skapat av en egen provkörning (t.ex. "Egna bolag" i
    LeadsRunForm.tsx med testkörningsflaggan på) ska aldrig kunna leda till
    ett utskick — även om någon glömmer växla tillbaka testläget innan
    körningen når sändvägen.
    """
    storage = MemoryStorage()
    item_id, thread_id, message_id = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    provider = _FakeSendProvider()

    provkorning = await storage.create_prospect(
        TENANT, company_name="Nordvik Bygg AB", origin="test"
    )
    storage.outreach_threads[TENANT][thread_id]["prospect_id"] = provkorning["id"]

    outcome = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert outcome == "blocked"
    assert provider.sent == []
    queue_item = next(i for i in storage.send_queue[TENANT] if i["id"] == item_id)
    assert queue_item["status"] == "blocked"
    assert queue_item["gate_checks"]["send_guard_regel"] == "testkorning"
    message = next(m for m in storage.outreach_messages[TENANT] if m["id"] == message_id)
    assert message["sent_at"] is None


@pytest.mark.anyio
async def test_riktigt_prospekt_pa_samma_trad_skickas():
    """Kontrollen ovan får inte vara en spärr som stoppar allt.

    Samma tråd, samma text, samma klocka — enda skillnaden är att prospektet
    är `origin='manual'`. Utan det här testet hade en spärr som blockerar
    varenda utskick sett lika grön ut som en som blockerar rätt.
    """
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    provider = _FakeSendProvider()

    riktigt = await storage.create_prospect(TENANT, company_name="Riktiga Bolaget AB")
    storage.outreach_threads[TENANT][thread_id]["prospect_id"] = riktigt["id"]

    outcome = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert outcome == "sent"
    assert len(provider.sent) == 1
