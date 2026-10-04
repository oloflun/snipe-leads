"""Kopian till Skickat (IMAP APPEND): utskick via Resend/SMTP passerar aldrig
kundens Gmail, så "Skickat" i mejlklienten stod tomt. Efter varje RIKTIG
sändning läggs nu en kopia i den kopplade inkorgens Skickat-mapp med samma
app-lösenord som synken använder.

Kontrakt:
  * Mappen hittas via \\Sent-attributet i LIST (RFC 6154) — namnet är
    lokaliserat (svensk Gmail: "[Gmail]/Skickat") och får aldrig hårdkodas
    som enda väg.
  * Kopian är en bekvämlighet: den får ALDRIG fälla eller fördröja en
    sändning, och den körs bara när providern faktiskt levererar.
  * Ingen kopplad inkorg = inget försök, ingen varning i kundens UI.
"""

from __future__ import annotations

import imaplib
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.email_pipeline import skickatkopia
from app.email_pipeline.connectors import imap as imap_connector
from app.email_pipeline.connectors.imap import _skickatmapp
from app.email_pipeline.skickatkopia import kopiera_till_skickat
from app.integrationer.hemligheter import kryptera
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

TENANT = "tenant-umea"
APP_LOSENORD = "abcdefghijklmnop"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeImapClient:
    """Minimal IMAP-klient: list/login/append/logout, allt inspelat."""

    def __init__(self, list_rader: list[bytes], *, append_svar: str = "OK"):
        self.list_rader = list_rader
        self.append_svar = append_svar
        self.anrop: list[tuple] = []

    def login(self, user, password):
        self.anrop.append(("login", user, password))
        return "OK", [b"Logged in"]

    def list(self):
        return "OK", self.list_rader

    def append(self, mailbox, flags, date_time, message):
        self.anrop.append(("append", mailbox, flags, message))
        if self.append_svar != "OK":
            raise imaplib.IMAP4.error("APPEND nekades")
        return "OK", [b"APPEND completed"]

    def logout(self):
        self.anrop.append(("logout",))
        return "BYE", []


GMAIL_SVENSK_LIST = [
    rb'(\HasNoChildren) "/" "INBOX"',
    rb'(\HasChildren \Noselect) "/" "[Gmail]"',
    rb'(\HasNoChildren \All) "/" "[Gmail]/Alla mail"',
    rb'(\HasNoChildren \Sent) "/" "[Gmail]/Skickat"',
    rb'(\HasNoChildren \Trash) "/" "[Gmail]/Papperskorgen"',
]


def test_skickatmapp_hittar_lokaliserad_gmailmapp():
    klient = _FakeImapClient(GMAIL_SVENSK_LIST)
    assert _skickatmapp(klient) == "[Gmail]/Skickat"


def test_skickatmapp_utan_sent_attribut_ger_none():
    klient = _FakeImapClient([rb'(\HasNoChildren) "/" "INBOX"'])
    assert _skickatmapp(klient) is None


async def test_spara_i_skickat_appendar_med_seen(monkeypatch):
    klient = _FakeImapClient(GMAIL_SVENSK_LIST)
    monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host, timeout=30: klient)

    fel = await imap_connector.spara_i_skickat(
        "imap.gmail.com",
        "umeawebdesign@gmail.com",
        APP_LOSENORD,
        fran="hej@snajp.se",
        till="prospect@example.se",
        amne="En idé till er",
        brodtext="Hej!\n\nMvh",
    )
    assert fel is None

    append = [a for a in klient.anrop if a[0] == "append"]
    assert len(append) == 1
    _, mapp, flaggor, meddelande = append[0]
    assert mapp == '"[Gmail]/Skickat"'
    assert "\\Seen" in flaggor
    assert b"To: prospect@example.se" in meddelande
    assert b"From: hej@snajp.se" in meddelande
    assert b"Subject: " in meddelande


async def test_spara_i_skickat_kastar_aldrig(monkeypatch):
    """Ett IMAP-fel blir en returnerad text — kopian får aldrig fälla sändningen."""
    klient = _FakeImapClient(GMAIL_SVENSK_LIST, append_svar="NO")
    monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host, timeout=30: klient)
    fel = await imap_connector.spara_i_skickat(
        "imap.gmail.com", "a@gmail.com", APP_LOSENORD,
        fran="x@y.se", till="b@c.se", amne="Ä", brodtext="t",
    )
    assert fel is not None


async def test_kopiera_till_skickat_anvander_kopplad_inkorg(monkeypatch):
    storage = MemoryStorage()
    storage.tenants[TENANT] = {"id": TENANT, "slug": "umeawebdesign", "name": "Umeå Webdesign"}
    await storage.upsert_mailbox(
        TENANT,
        provider="gmail",
        address="umeawebdesign@gmail.com",
        secret_enc=kryptera({"losenord": APP_LOSENORD}),
    )

    anrop: list[dict] = []

    async def fejk(host, user, password, **kwargs):
        anrop.append({"host": host, "user": user, "password": password, **kwargs})
        return None

    monkeypatch.setattr(imap_connector, "spara_i_skickat", fejk)

    fel = await kopiera_till_skickat(
        storage, TENANT, till="prospect@example.se", amne="En idé", brodtext="Hej!",
        fran="hej@snajp.se",
    )
    assert fel is None
    assert anrop == [
        {
            "host": "imap.gmail.com",
            "user": "umeawebdesign@gmail.com",
            "password": APP_LOSENORD,
            "fran": "hej@snajp.se",
            "till": "prospect@example.se",
            "amne": "En idé",
            "brodtext": "Hej!",
        }
    ]


async def test_kopian_valjer_inkorg_efter_syfte(monkeypatch):
    """Migration 084: leadsutskick i leadsinkorgen, supportsvar i supportinkorgen."""
    storage = MemoryStorage()
    storage.tenants[TENANT] = {"id": TENANT, "slug": "umeawebdesign", "name": "Umeå Webdesign"}
    for adress, syfte in (("support@kund.se", "support"), ("salj@kund.se", "leads")):
        await storage.upsert_mailbox(
            TENANT, provider="gmail", address=adress, secret_enc=kryptera({"losenord": APP_LOSENORD}), syfte=syfte,
        )
    anrop: list[str] = []

    async def fejk(host, user, password, **kwargs):
        anrop.append(user)
        return None

    monkeypatch.setattr(imap_connector, "spara_i_skickat", fejk)
    await kopiera_till_skickat(storage, TENANT, till="p@x.se", amne="a", brodtext="b", syfte="leads")
    await kopiera_till_skickat(storage, TENANT, till="p@x.se", amne="a", brodtext="b")
    assert anrop == ["salj@kund.se", "support@kund.se"]


async def test_kopiera_utan_inkorg_gor_ingenting(monkeypatch):
    storage = MemoryStorage()
    storage.tenants[TENANT] = {"id": TENANT, "slug": "umeawebdesign"}

    async def exploderar(*args, **kwargs):  # pragma: no cover - ska aldrig nås
        raise AssertionError("ingen inkorg = inget IMAP-anrop")

    monkeypatch.setattr(imap_connector, "spara_i_skickat", exploderar)
    assert await kopiera_till_skickat(storage, TENANT, till="a@b.se", amne="x", brodtext="y") is None


async def test_kopiera_hoppar_over_mockinkorgar(monkeypatch):
    storage = MemoryStorage()
    storage.tenants[TENANT] = {"id": TENANT, "slug": "umeawebdesign"}
    await storage.upsert_mailbox(TENANT, provider="mock", address="demo@example.se")

    async def exploderar(*args, **kwargs):  # pragma: no cover
        raise AssertionError("mock-inkorgen får aldrig nås över IMAP")

    monkeypatch.setattr(imap_connector, "spara_i_skickat", exploderar)
    assert await kopiera_till_skickat(storage, TENANT, till="a@b.se", amne="x", brodtext="y") is None


async def test_supportsvar_lagger_kopia_i_skickat(monkeypatch):
    """Sändvägen för supportsvar anropar kopian efter en lyckad riktig sändning."""
    from app.email_pipeline.sender import skicka_supportsvar

    anrop: list[dict] = []

    async def fejk_kopia(storage, tenant_id, *, till, amne, brodtext, fran=""):
        anrop.append({"tenant_id": tenant_id, "till": till, "amne": amne})
        return None

    monkeypatch.setattr(skickatkopia, "kopiera_till_skickat", fejk_kopia)

    class _Skickare:
        levererar = True

        async def send(self, *, to, subject, body):
            return None

    storage = MemoryStorage()
    storage.tenants[TENANT] = {"id": TENANT, "slug": "umeawebdesign"}
    notering = await skicka_supportsvar(
        {"id": "e-1", "provider": "imap", "from_email": "kund@example.com", "subject": "Fråga"},
        content="Svar.",
        tenant_id=TENANT,
        storage=storage,
        provider=_Skickare(),
    )
    assert "Skickat till kund@example.com" in notering
    assert anrop == [{"tenant_id": TENANT, "till": "kund@example.com", "amne": "Re: Fråga"}]


async def test_simulerad_sandning_lagger_ingen_kopia(monkeypatch):
    """LoggingSendProvider skickar inget riktigt — då ska Skickat inte ljuga."""
    from app.email_pipeline.sender import skicka_supportsvar
    from app.leads.send_provider import LoggingSendProvider

    async def exploderar(*args, **kwargs):  # pragma: no cover
        raise AssertionError("simulerad sändning får ingen Skickat-kopia")

    monkeypatch.setattr(skickatkopia, "kopiera_till_skickat", exploderar)
    storage = MemoryStorage()
    storage.tenants[TENANT] = {"id": TENANT, "slug": "umeawebdesign"}
    await skicka_supportsvar(
        {"id": "e-1", "provider": "imap", "from_email": "kund@example.com", "subject": "Fråga"},
        content="Svar.",
        tenant_id=TENANT,
        storage=storage,
        provider=LoggingSendProvider(),
    )
