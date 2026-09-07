"""Synkstämpeln: last_sync_at/last_error skrevs aldrig av någon kodväg.

Upptäckt 2026-09-07: en bevakning läste last_sync_at=null och drog slutsatsen
att pollern var död — fast den hade hämtat mail. Kundens "senaste synk" stod
tom för evigt, och ett fel lösenord var helt tyst.
"""

from __future__ import annotations

import pytest

from app.email_pipeline import poller
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _brevlada(storage, **overrides):
    rad = {
        "id": "mb-1", "tenant_id": TENANT, "provider": "gmail",
        "address": "support@example.com", "status": "active",
        "last_sync_at": None, "last_error": None,
    }
    rad.update(overrides)
    storage.mailboxes[rad["id"]] = rad
    return rad


async def test_lyckad_synk_stamplar_utan_fel(monkeypatch):
    storage = MemoryStorage()
    rad = await _brevlada(storage)

    async def inga_nya(*args, **kwargs):
        return [], None

    monkeypatch.setattr(poller.imap, "fetch_new", inga_nya)
    monkeypatch.setenv(poller.password_env_name("nordlys-handel"), "app-losenord")
    resultat = await poller.sync_mailbox(storage, TENANT, "nordlys-handel", rad)

    assert resultat["error"] is None
    assert rad["last_sync_at"] is not None
    assert rad["last_error"] is None


async def test_saknat_losenord_stamplar_felet(monkeypatch):
    """Det är exakt det här kundens UI behöver kunna visa: inte "aldrig
    synkad" utan VARFÖR ingen synk sker."""
    storage = MemoryStorage()
    rad = await _brevlada(storage, id="mb-2")
    monkeypatch.delenv(poller.password_env_name("nordlys-handel"), raising=False)

    resultat = await poller.sync_mailbox(storage, TENANT, "nordlys-handel", rad)

    assert "saknas" in (resultat["error"] or "")
    assert rad["last_sync_at"] is not None
    assert "saknas" in (rad["last_error"] or "")


async def test_imapfel_stamplar_felet(monkeypatch):
    storage = MemoryStorage()
    rad = await _brevlada(storage, id="mb-3")

    async def spricker(*args, **kwargs):
        return [], "inloggningen avvisades"

    monkeypatch.setattr(poller.imap, "fetch_new", spricker)
    monkeypatch.setenv(poller.password_env_name("nordlys-handel"), "fel-losenord")
    resultat = await poller.sync_mailbox(storage, TENANT, "nordlys-handel", rad)

    assert rad["last_error"] == "inloggningen avvisades"
    assert rad["last_sync_at"] is not None


async def test_stampeln_faller_aldrig_synken(monkeypatch):
    """Resultatet är redan framme — en trasig statistikskrivning får inte
    kasta bort det."""
    storage = MemoryStorage()
    rad = await _brevlada(storage, id="mb-4")

    async def inga_nya(*args, **kwargs):
        return [], None

    async def stampel_spricker(*args, **kwargs):
        raise RuntimeError("databasen borta")

    monkeypatch.setattr(poller.imap, "fetch_new", inga_nya)
    monkeypatch.setattr(storage, "touch_mailbox_sync", stampel_spricker)
    monkeypatch.setenv(poller.password_env_name("nordlys-handel"), "app-losenord")

    resultat = await poller.sync_mailbox(storage, TENANT, "nordlys-handel", rad)
    assert resultat["fetched"] == 0 and resultat["error"] is None
