"""Läst-markeringens ordning: EFTER ingest, aldrig före.

Den gamla vägen satte \\Seen i samma varv som hämtningen (fetch utan PEEK plus
ett uttryckligt store). Föll databasen mellan hämtning och ingest var mejlet
markerat läst på servern och UNSEEN-sökningen såg det aldrig igen — ett tappat
kundmejl utan spår. Nu hämtar _fetch_sync med BODY.PEEK och pollern markerar
via mark_seen() först när raden står i databasen.
"""

from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from app.email_pipeline import poller
from app.email_pipeline.connectors import imap
from app.email_pipeline.models import InboundEmail
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _rfc822(message_id: str = "<orig-123@example.com>") -> bytes:
    m = EmailMessage()
    m["From"] = "Kund <kund@example.com>"
    m["Subject"] = "Var är mitt paket?"
    m["Message-ID"] = message_id
    m.set_content("Hej, var är paketet?")
    return bytes(m)


def test_fetch_peekar_och_markerar_inte():
    client = MagicMock()

    def uid(kommando, *args):
        if kommando == "search":
            return ("OK", [b"7"])
        if kommando == "fetch":
            return ("OK", [(b"7 (BODY[] {42}", _rfc822())])
        raise AssertionError(f"Oväntat uid-kommando i hämtvarvet: {kommando}")

    client.uid.side_effect = uid
    with patch.object(imap.imaplib, "IMAP4_SSL", return_value=client):
        [mejl] = imap._fetch_sync("imap.gmail.com", "a@example.com", "pw", "INBOX")

    assert mejl.imap_uid == "7"
    assert mejl.provider_message_id == "<orig-123@example.com>"
    # Hämtningen rör aldrig flaggorna: inget store, och fetch sker med PEEK.
    kommandon = [anrop.args[0] for anrop in client.uid.call_args_list]
    assert "store" not in kommandon
    fetch_anrop = [anrop for anrop in client.uid.call_args_list if anrop.args[0] == "fetch"]
    assert all("PEEK" in anrop.args[2] for anrop in fetch_anrop)
    client.store.assert_not_called()


async def test_mark_seen_stampplar_uid_med_seen():
    client = MagicMock()
    with patch.object(imap.imaplib, "IMAP4_SSL", return_value=client):
        fel = await imap.mark_seen("imap.gmail.com", "a@example.com", "pw", "INBOX", ["7", "9"])
    assert fel is None
    client.uid.assert_any_call("store", "7,9", "+FLAGS", "\\Seen")


async def test_mark_seen_utan_uids_oppnar_ingen_anslutning():
    with patch.object(imap.imaplib, "IMAP4_SSL") as ssl:
        assert await imap.mark_seen("imap.gmail.com", "a@example.com", "pw", "INBOX", []) is None
    ssl.assert_not_called()


def _mailbox() -> dict:
    return {
        "id": "mb-1",
        "address": "kund@example.com",
        "provider": "gmail",
        "imap_host": "imap.gmail.com",
        "status": "active",
        "secret_enc": None,
    }


def _inbound(uid: str, message_id: str) -> InboundEmail:
    return InboundEmail(
        provider="imap",
        provider_message_id=message_id,
        from_email="kund@example.com",
        from_name="Kund",
        subject="Fråga",
        body_text="Hej",
        imap_uid=uid,
    )


async def _tenant(storage: MemoryStorage) -> str:
    tenant = await storage.create_tenant(slug="nordlys-handel", name="Nordlys")
    return tenant["id"]


async def test_sync_markerar_efter_ingest(monkeypatch):
    storage = MemoryStorage()
    tenant_id = await _tenant(storage)
    monkeypatch.setenv("IMAP_PASSWORD_NORDLYS_HANDEL", "pw")

    async def tva_mail(*args, **kwargs):
        return [_inbound("7", "<a@x>"), _inbound("9", "<b@x>")], None

    markerade: list[list[str]] = []

    async def fange_mark(host, user, password, folder, uids, **kwargs):
        markerade.append(list(uids))
        return None

    monkeypatch.setattr(poller.imap, "fetch_new", tva_mail)
    monkeypatch.setattr(poller.imap, "mark_seen", fange_mark)

    resultat = await poller.sync_mailbox(
        storage, tenant_id, "nordlys-handel", _mailbox(), bearbeta=False
    )
    assert resultat["fetched"] == 2
    assert markerade == [["7", "9"]]


async def test_trasig_ingest_markerar_bara_det_som_sparats(monkeypatch):
    storage = MemoryStorage()
    tenant_id = await _tenant(storage)
    monkeypatch.setenv("IMAP_PASSWORD_NORDLYS_HANDEL", "pw")

    async def tva_mail(*args, **kwargs):
        return [_inbound("7", "<a@x>"), _inbound("9", "<b@x>")], None

    riktig_ingest = poller.ingest_email

    async def spricker_pa_andra(storage_, tenant_id_, message, **kwargs):
        if message.imap_uid == "9":
            raise RuntimeError("databasen föll")
        return await riktig_ingest(storage_, tenant_id_, message, **kwargs)

    markerade: list[list[str]] = []

    async def fange_mark(host, user, password, folder, uids, **kwargs):
        markerade.append(list(uids))
        return None

    monkeypatch.setattr(poller, "ingest_email", spricker_pa_andra)
    monkeypatch.setattr(poller.imap, "fetch_new", tva_mail)
    monkeypatch.setattr(poller.imap, "mark_seen", fange_mark)

    resultat = await poller.sync_mailbox(
        storage, tenant_id, "nordlys-handel", _mailbox(), bearbeta=False
    )
    # Mejl 9 sparades aldrig och får INTE markeras läst — det ska hämtas om.
    assert markerade == [["7"]]
    assert "kunde inte sparas" in (resultat["error"] or "")


async def test_dublett_markeras_sa_den_inte_klampar_i_fonstret(monkeypatch):
    storage = MemoryStorage()
    tenant_id = await _tenant(storage)
    monkeypatch.setenv("IMAP_PASSWORD_NORDLYS_HANDEL", "pw")

    async def samma_mail(*args, **kwargs):
        return [_inbound("7", "<a@x>")], None

    markerade: list[list[str]] = []

    async def fange_mark(host, user, password, folder, uids, **kwargs):
        markerade.append(list(uids))
        return None

    monkeypatch.setattr(poller.imap, "fetch_new", samma_mail)
    monkeypatch.setattr(poller.imap, "mark_seen", fange_mark)

    await poller.sync_mailbox(storage, tenant_id, "nordlys-handel", _mailbox(), bearbeta=False)
    # Andra varvet: ingest ser dubletten (None) men uid:t markeras ändå —
    # annars står ett redan sparat mejl olästa kvar i 20-mejlsfönstret för evigt.
    await poller.sync_mailbox(storage, tenant_id, "nordlys-handel", _mailbox(), bearbeta=False)
    assert markerade == [["7"], ["7"]]
