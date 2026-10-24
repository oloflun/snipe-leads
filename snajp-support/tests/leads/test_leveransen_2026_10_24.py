"""Leveransdelen (Sebbe 2026-10-24, docs/UTSKICK-SVARSFREKVENS-DIAGNOS-2026-10-24.md).

~600 kallmejl gav 2 mänskliga svar och knappt några autosvar. Tre rättningar
i sändvägen:

- det första mejlet i en tråd går som ren text, utan HTML och logotyp;
- varje utskick bär taggar (tenant, meddelande) som Resends webhook skickar
  tillbaka, så att en studs eller ett klagomål hamnar på rätt meddelande
  och adressen spärras;
- leveransstoppet (send_guard regel 5e) läser utfallet ur lagret."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.leads.scheduler import skicka_godkant
from app.sending_domains import apply_email_event
from app.storage.memory import MemoryStorage
from tests.leads.test_scheduler import TENANT, WITHIN_WINDOW_UTC, _seed

pytestmark = pytest.mark.anyio

SIGNATUR = {
    "aktiv": True, "namn": "Anna Andersson", "bolag": "Snajp AB",
    "logotyp_url": "https://example.se/logga.png",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _ResendLik:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, *, to, subject, body, html=None, tags=None, **_):
        self.sent.append({"to": to, "html": html, "tags": tags})


async def _godkant_utkast(storage: MemoryStorage) -> tuple[str, str]:
    item_id, thread_id, _ = _seed(storage, autonomy="draft", scheduled_at=WITHIN_WINDOW_UTC)
    storage.outreach_messages[TENANT] = [m for m in storage.outreach_messages[TENANT] if m["thread_id"] != "historik"]
    storage.send_queue[TENANT][-1]["status"] = "awaiting_review"
    storage.agent_settings[(TENANT, "leads")] = {
        **storage.agent_settings.get((TENANT, "leads"), {}), "signatur": SIGNATUR,
    }
    return item_id, thread_id


async def test_forsta_mejlet_gar_som_ren_text_med_taggar():
    storage, provider = MemoryStorage(), _ResendLik()
    item_id, _ = await _godkant_utkast(storage)

    utfall, skal = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    assert utfall == "sent", skal
    [mejl] = provider.sent
    assert mejl["html"] is None
    taggar = {t["name"]: t["value"] for t in mejl["tags"]}
    assert taggar["tenant"] == str(TENANT)
    meddelande = next(m for m in storage.outreach_messages[TENANT] if m.get("sent_at"))
    assert taggar["meddelande"] == meddelande["id"]


async def test_uppfoljningen_bar_logotypen():
    storage, provider = MemoryStorage(), _ResendLik()
    item_id, thread_id = await _godkant_utkast(storage)
    storage.outreach_messages[TENANT].insert(0, {
        "id": str(uuid.uuid4()), "tenant_id": TENANT, "thread_id": thread_id, "direction": "outbound",
        "body": "Första.", "subject": "Hej", "sent_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
    })

    utfall, skal = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    assert utfall == "sent", skal
    assert "logga.png" in (provider.sent[0]["html"] or "")


def _handelse(typ: str, *, tenant: str, meddelande: str, bounce_typ: str = "Permanent") -> dict:
    data = {"to": ["lead@bolaget.se"], "tags": {"tenant": tenant, "meddelande": meddelande}}
    if typ == "email.bounced":
        data["bounce"] = {"type": bounce_typ}
    return {"type": typ, "data": data}


async def _skickat_meddelande(storage: MemoryStorage) -> str:
    storage.outreach_messages.setdefault(TENANT, []).append({
        "id": (mid := str(uuid.uuid4())), "tenant_id": TENANT, "thread_id": "t", "direction": "outbound",
        "body": "x", "subject": "y", "sent_at": datetime.now(timezone.utc),
    })
    return mid


async def test_studs_markeras_och_adressen_sparras():
    storage = MemoryStorage()
    mid = await _skickat_meddelande(storage)

    assert await apply_email_event(storage, _handelse("email.bounced", tenant=TENANT, meddelande=mid))

    assert await storage.leveransutfall(TENANT) == {"skickade": 1, "studsade": 1, "klagomal": 0}
    assert "lead@bolaget.se" in await storage.list_suppressions(TENANT)


async def test_klagomal_skrivs_inte_over_av_en_studs():
    storage = MemoryStorage()
    mid = await _skickat_meddelande(storage)
    await apply_email_event(storage, _handelse("email.complained", tenant=TENANT, meddelande=mid))
    await apply_email_event(storage, _handelse("email.bounced", tenant=TENANT, meddelande=mid))
    assert await storage.leveransutfall(TENANT) == {"skickade": 1, "studsade": 0, "klagomal": 1}


async def test_tillfallig_studs_och_otaggad_handelse_ignoreras():
    storage = MemoryStorage()
    mid = await _skickat_meddelande(storage)
    tillfallig = _handelse("email.bounced", tenant=TENANT, meddelande=mid, bounce_typ="Transient")
    assert not await apply_email_event(storage, tillfallig)
    assert not await apply_email_event(storage, {"type": "email.bounced", "data": {"to": ["x@y.se"]}})
    assert not await apply_email_event(storage, _handelse("email.delivered", tenant=TENANT, meddelande=mid))
    assert await storage.leveransutfall(TENANT) == {"skickade": 1, "studsade": 0, "klagomal": 0}
    assert not await storage.list_suppressions(TENANT)


async def test_ett_klagomal_pausar_nasta_utskick():
    storage, provider = MemoryStorage(), _ResendLik()
    item_id, _ = await _godkant_utkast(storage)
    mid = await _skickat_meddelande(storage)
    await apply_email_event(storage, _handelse("email.complained", tenant=TENANT, meddelande=mid))

    utfall, skal = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    assert utfall != "sent" and not provider.sent
    assert "pausade" in (skal or "")


class _KolumnSaknas(Exception):
    sqlstate = "42703"


async def test_saknad_kolumn_ger_fel_sa_att_resend_forsoker_igen():
    """Migration 113 inte körd: webhooken ska fela (Resend skickar igen), inte
    tyst svara att händelsen hanterats."""
    storage = MemoryStorage()

    async def kastar(*_a, **_k):
        raise _KolumnSaknas()

    storage.markera_leverans = kastar
    with pytest.raises(_KolumnSaknas):
        await apply_email_event(storage, _handelse("email.bounced", tenant=TENANT, meddelande=str(uuid.uuid4())))


async def test_leveransutfall_utan_kolumn_ger_nollor(monkeypatch):
    """Postgres utan migration 113: läsningen före varje utskick ska inte
    stoppa utskicken."""
    import asyncpg

    from app.storage.postgres import PostgresStorage

    class _Conn:
        async def fetchrow(self, *_a, **_k):
            raise asyncpg.UndefinedColumnError("column \"leverans\" does not exist")

    class _Scope:
        async def __aenter__(self):
            return _Conn()

        async def __aexit__(self, *_a):
            return False

    lagring = PostgresStorage.__new__(PostgresStorage)
    monkeypatch.setattr(lagring, "_scoped", lambda _t: _Scope(), raising=False)
    assert await lagring.leveransutfall("t") == {"skickade": 0, "studsade": 0, "klagomal": 0}
