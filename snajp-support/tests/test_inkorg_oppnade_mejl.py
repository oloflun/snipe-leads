"""Hämtningen efter UID och mejl som redan var öppnade (migration 150).

Antons beställning 2026-11-23: "Bygg om hämtningen, men se till att supporten
ser de vi öppnat och därmed inte skriver utkast på dem utan sorterar till
manuell hantering."

Sökningen på olästa (UNSEEN) tappade varje mejl som en människa hann öppna i
brevlådan före synken. Nu ska

  1. allt med högre UID än brevlådans märke hämtas, läst eller inte;
  2. en brevlåda utan märke börja med olästa plus de senaste dagarna;
  3. märket bara flyttas förbi det som står i databasen;
  4. ett mejl som var läst på servern bära `last_i_brevladan`, gå till Att
     hantera utan utkast (support) eller lämnas över i konversationen utan
     utkast (leads), och ändå klassas så att en avregistrering gäller.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import DEFAULT_TENANT_ID
from app.email_pipeline import poller, processor
from app.email_pipeline.connectors import imap
from app.email_pipeline.models import InboundEmail
from app.email_pipeline.processor import process_email
from app.leads.svar import hantera_prospektsvar
from app.storage.memory import MemoryStorage

from tests.leads.test_svar import _stegsvar

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Hämtningen ---------------------------------------------------------------


def _rfc822(message_id: str) -> bytes:
    m = EmailMessage()
    m["From"] = "Kund <kund@example.com>"
    m["Subject"] = "Var är mitt paket?"
    m["Message-ID"] = message_id
    m.set_content("Hej, var är paketet?")
    return bytes(m)


def _klient(sokresultat: bytes, mejl: dict[bytes, list], *, uidvalidity: bytes = b"3", uidnext: bytes = b"20"):
    """En IMAP-klient som svarar på search och fetch och minns sökningen."""
    client = MagicMock()
    client.sokningar = []

    def uid(kommando, *args):
        if kommando == "search":
            client.sokningar.append(args[1:])
            return ("OK", [sokresultat])
        if kommando == "fetch":
            return ("OK", mejl[args[0]])
        raise AssertionError(f"Oväntat uid-kommando i hämtvarvet: {kommando}")

    client.uid.side_effect = uid
    client.response.side_effect = lambda kod: (kod, [{"UIDVALIDITY": uidvalidity, "UIDNEXT": uidnext}[kod]])
    return client


def test_med_marke_hamtas_allt_med_hogre_uid_ocksa_det_lasta():
    client = _klient(
        b"8 9",
        {
            b"8": [(b"1 (UID 8 FLAGS (\\Seen) BODY[] {42}", _rfc822("<last@x>")), b")"],
            # Vissa servrar lägger flaggorna efter kroppen.
            b"9": [(b"2 (UID 9 BODY[] {42}", _rfc822("<olast@x>")), b" FLAGS (\\Recent))"],
        },
    )
    tillstand: dict = {}
    with patch.object(imap.imaplib, "IMAP4_SSL", return_value=client):
        mejl = imap._fetch_sync(
            "imap.gmail.com", "a@example.com", "pw", "INBOX",
            efter_uid=7, uidvalidity=3, tillbakablick_dagar=7, tillstand=tillstand,
        )

    assert client.sokningar == [("UID", "8:*")]
    assert [(m.imap_uid, m.last_i_brevladan) for m in mejl] == [("8", True), ("9", False)]
    assert tillstand["market_galler"] and tillstand["uidvalidity"] == 3 and tillstand["uidnext"] == 20
    # Hämtningen rör fortfarande inga flaggor.
    assert "store" not in [anrop.args[0] for anrop in client.uid.call_args_list]


def test_sista_mejlet_under_market_hamtas_inte_om():
    """`UID n:*` ger alltid mappens sista mejl, också när dess UID är lägre än n."""
    client = _klient(b"7", {})
    with patch.object(imap.imaplib, "IMAP4_SSL", return_value=client):
        assert imap._fetch_sync("imap.gmail.com", "a@example.com", "pw", "INBOX", efter_uid=7, uidvalidity=3) == []


def test_utan_marke_soks_olasta_och_de_senaste_dagarna():
    client = _klient(b"5", {b"5": [(b"1 (UID 5 FLAGS (\\Seen) BODY[] {42}", _rfc822("<a@x>"))]})
    with patch.object(imap.imaplib, "IMAP4_SSL", return_value=client):
        [mejl] = imap._fetch_sync("imap.gmail.com", "a@example.com", "pw", "INBOX", tillbakablick_dagar=7)

    [sokning] = client.sokningar
    assert sokning[:3] == ("OR", "UNSEEN", "SINCE")
    fran = datetime.now(timezone.utc).date() - timedelta(days=7)
    assert sokning[3] == imap._imapdatum(fran)
    assert mejl.last_i_brevladan


def test_bytt_uidvalidity_gor_market_ogiltigt():
    client = _klient(b"", {}, uidvalidity=b"4")
    tillstand: dict = {}
    with patch.object(imap.imaplib, "IMAP4_SSL", return_value=client):
        imap._fetch_sync(
            "imap.gmail.com", "a@example.com", "pw", "INBOX",
            efter_uid=900, uidvalidity=3, tillbakablick_dagar=7, tillstand=tillstand,
        )
    assert client.sokningar[0][:3] == ("OR", "UNSEEN", "SINCE")
    assert not tillstand["market_galler"] and tillstand["uidvalidity"] == 4


def test_imapdatum_ar_engelskt_oavsett_locale():
    assert imap._imapdatum(datetime(2026, 5, 3).date()) == "03-May-2026"
    assert imap._imapdatum(datetime(2026, 10, 16).date()) == "16-Oct-2026"


# -- Märket i pollern ---------------------------------------------------------


def _inbound(uid: str, message_id: str, *, last: bool = False) -> InboundEmail:
    return InboundEmail(
        provider="imap", provider_message_id=message_id, from_email="kund@example.com",
        from_name="Kund", subject="Fråga", body_text="Hej", imap_uid=uid, last_i_brevladan=last,
    )


async def _brevlada(storage: MemoryStorage, monkeypatch) -> tuple[str, dict]:
    tenant = await storage.create_tenant(slug="nordlys-handel", name="Nordlys")
    monkeypatch.setenv("IMAP_PASSWORD_NORDLYS_HANDEL", "pw")
    monkeypatch.setattr(poller.imap, "mark_seen", AsyncMock(return_value=None))
    brevlada = await storage.upsert_mailbox(
        tenant["id"], provider="gmail", address="kund@example.com", imap_host="imap.gmail.com"
    )
    return tenant["id"], brevlada


async def test_market_flyttas_efter_ingest_och_foljer_med_till_nasta_synk(monkeypatch):
    storage = MemoryStorage()
    tenant_id, brevlada = await _brevlada(storage, monkeypatch)
    anrop: list[dict] = []

    async def hamta(*args, **kwargs):
        anrop.append(kwargs)
        kwargs["tillstand"].update(uidvalidity=3, uidnext=10, market_galler=kwargs["efter_uid"] is not None)
        return ([_inbound("7", "<a@x>"), _inbound("9", "<b@x>", last=True)], None) if len(anrop) == 1 else ([], None)

    monkeypatch.setattr(poller.imap, "fetch_new", hamta)

    await poller.sync_mailbox(storage, tenant_id, "nordlys-handel", brevlada, bearbeta=False)
    [rad] = await storage.list_mailboxes(tenant_id)
    assert (rad["imap_last_uid"], rad["imap_uidvalidity"]) == (9, 3)
    assert anrop[0]["efter_uid"] is None and anrop[0]["tillbakablick_dagar"] == 7

    await poller.sync_mailbox(storage, tenant_id, "nordlys-handel", rad, bearbeta=False)
    assert anrop[1]["efter_uid"] == 9 and anrop[1]["uidvalidity"] == 3
    # Flaggan står på raden, så bearbetningen i bakgrunden ser den.
    sparade = {e["provider_message_id"]: e for e in storage.emails.values()}
    assert sparade["<b@x>"]["last_i_brevladan"] and not sparade["<a@x>"]["last_i_brevladan"]


async def test_market_stannar_vid_mejlet_som_inte_gick_att_spara(monkeypatch):
    storage = MemoryStorage()
    tenant_id, brevlada = await _brevlada(storage, monkeypatch)

    async def hamta(*args, **kwargs):
        kwargs["tillstand"].update(uidvalidity=3, uidnext=10, market_galler=False)
        return [_inbound("7", "<a@x>"), _inbound("9", "<b@x>")], None

    riktig_ingest = poller.ingest_email

    async def spricker_pa_andra(storage_, tenant_id_, message, **kwargs):
        if message.imap_uid == "9":
            raise RuntimeError("databasen föll")
        return await riktig_ingest(storage_, tenant_id_, message, **kwargs)

    monkeypatch.setattr(poller.imap, "fetch_new", hamta)
    monkeypatch.setattr(poller, "ingest_email", spricker_pa_andra)

    await poller.sync_mailbox(storage, tenant_id, "nordlys-handel", brevlada, bearbeta=False)
    [rad] = await storage.list_mailboxes(tenant_id)
    assert rad["imap_last_uid"] == 7  # mejl 9 hämtas om nästa synk


async def test_tom_brevlada_utan_marke_far_market_under_nasta_uid(monkeypatch):
    storage = MemoryStorage()
    tenant_id, brevlada = await _brevlada(storage, monkeypatch)

    async def hamta(*args, **kwargs):
        kwargs["tillstand"].update(uidvalidity=3, uidnext=41, market_galler=False)
        return [], None

    monkeypatch.setattr(poller.imap, "fetch_new", hamta)
    await poller.sync_mailbox(storage, tenant_id, "nordlys-handel", brevlada, bearbeta=False)
    [rad] = await storage.list_mailboxes(tenant_id)
    assert (rad["imap_last_uid"], rad["imap_uidvalidity"]) == (40, 3)


async def test_ett_fel_i_hamtningen_ror_inte_market(monkeypatch):
    storage = MemoryStorage()
    tenant_id, brevlada = await _brevlada(storage, monkeypatch)
    await storage.satt_imap_marke(tenant_id, brevlada["id"], last_uid=12, uidvalidity=3)

    async def hamta(*args, **kwargs):
        return [], "IMAP-fel (utgången token/fel lösenord?)"

    monkeypatch.setattr(poller.imap, "fetch_new", hamta)
    [rad] = await storage.list_mailboxes(tenant_id)
    await poller.sync_mailbox(storage, tenant_id, "nordlys-handel", rad, bearbeta=False)
    [rad] = await storage.list_mailboxes(tenant_id)
    assert rad["imap_last_uid"] == 12


# -- Kundtjänsten: Att hantera, inget utkast ----------------------------------


async def _sparat(storage: MemoryStorage, *, last: bool, fran: str = "anna@example.com"):
    return await storage.save_email(
        DEFAULT_TENANT_ID, provider="imap", provider_message_id=f"oppnat-{fran}-{last}", from_email=fran,
        from_name="Anna Andersson", subject="Fråga om min order", body_text="Hej, var är mitt paket?",
        last_i_brevladan=last,
    )


async def test_oppnat_supportmejl_gar_till_att_hantera_utan_utkast(monkeypatch):
    storage = MemoryStorage()
    mail = await _sparat(storage, last=True)

    async def ingen_modell(*args, **kwargs):
        raise AssertionError("Triagen nåddes fast mejlet var öppnat i brevlådan")

    monkeypatch.setattr(processor, "_triage_email", ingen_modell)

    assert await process_email(storage, DEFAULT_TENANT_ID, mail) == {"action": "att_hantera"}

    sparat = await storage.get_email(DEFAULT_TENANT_ID, mail["id"])
    assert sparat["status"] == "att_hantera" and sparat["last_i_brevladan"] and not sparat["draft"]
    assert "last_i_brevladan" in [b["event"] for b in await storage.list_decisions(DEFAULT_TENANT_ID, mail["id"])]
    # Fliken Att hantera listar det; den vanliga inkorgen gör det inte.
    assert [e["id"] for e in await storage.list_emails(DEFAULT_TENANT_ID, status="att_hantera")] == [mail["id"]]
    assert await storage.list_emails(DEFAULT_TENANT_ID) == []


async def test_oppnat_nyhetsbrev_goms_som_forut():
    """Klassningen går före: ett utskick någon råkat öppna hör inte hemma i Att hantera."""
    storage = MemoryStorage()
    mail = await storage.save_email(
        DEFAULT_TENANT_ID, provider="imap", provider_message_id="nyhetsbrev-1", from_email="noreply@butik.example",
        from_name="Butiken", subject="Vårt nyhetsbrev vecka 47", body_text="Erbjudanden.", last_i_brevladan=True,
    )
    assert await process_email(storage, DEFAULT_TENANT_ID, mail) == {"action": "ej_relaterat"}


# -- Leads: svaret når konversationen, Iris skriver inget utkast --------------

TENANT = "00000000-0000-4000-a000-000000000001"


async def _trad(storage: MemoryStorage) -> tuple[str, str]:
    prospekt = await storage.create_prospect(TENANT, company_name="Telecom Buddy AB", contact_email="tomas@buddy.se")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
    koat = await storage.queue_outreach_message(
        TENANT, thread_id=trad["id"], body="Hej Tomas, en tanke om er kundtjänst.", subject="En tanke",
        humanizer_variant="snajp:humanizer-svenska", scheduled_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    await storage.mark_outreach_message_sent(TENANT, koat["message"]["id"], datetime.now(timezone.utc) - timedelta(days=5))
    await storage.update_send_queue_status(TENANT, koat["queue_item"]["id"], status="sent", gate_checks={})
    await storage.update_prospect(TENANT, prospekt["id"], status="contacted")
    return prospekt["id"], trad["id"]


async def _svara(storage, thread_id: str, body: str, klass: str, **kwargs):
    steg, anrop = _stegsvar({
        "sa:call-summary": {"klass": klass, "fraga_karna": "När passar ett möte?"},
        "mk:sales-enablement": {"subject": "Re: demo", "body": "Hej Tomas, passar måndag kl 10?"},
        "snajp:humanizer-svenska": {"final_subject": "Re: demo", "final_body": "Hej Tomas, passar måndag kl 10?"},
    })
    with patch("app.leads.svar.run_step", new=steg), patch(
        "app.leads.svar.skicka_prioriterat", new=AsyncMock(return_value=True)
    ) as mejl:
        utfall = await hantera_prospektsvar(
            storage, TENANT, thread_id=thread_id, body=body, tenant_name="Snajp",
            context_pack="## Kontextpaket\nSnajp säljer AI-support. Möte måndag kl 10 demo.", **kwargs,
        )
    return utfall, anrop, mejl


async def test_oppnat_svar_fran_lead_sparas_och_klassas_men_far_inget_utkast():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)

    utfall, _, mejl = await _svara(storage, tid, "Hej, kan ni visa en demo?", "fraga", utan_utkast=True)

    assert utfall["klass"] == "fraga" and not utfall["queued"] and utfall["handoff"]
    assert utfall["eskalerat"] == ["last_i_brevladan"]
    assert await storage.get_pending_outreach_message(TENANT, tid) is None
    # Svaret står i tråden och leadet har flyttats till Svarat.
    assert [m["direction"] for m in await storage.list_outreach_messages(TENANT, tid)] == ["outbound", "inbound"]
    assert (await storage.get_prospect(TENANT, pid))["status"] == "replied"
    # Konversationen säger varför det inte finns något utkast.
    handelser = {h["typ"]: h for h in await storage.list_handelser(TENANT, thread_id=tid)}
    assert handelser["svar"]["detalj"]["last_i_brevladan"] is True
    assert handelser["overlamnat"]["detalj"]["eskalerat"] == ["last_i_brevladan"]
    assert "utkast" not in handelser
    # Den som öppnade svaret vet redan om det: inget prioriterat mejl.
    mejl.assert_not_called()


async def test_samma_svar_oppnat_av_ingen_far_utkast_som_forut():
    storage = MemoryStorage()
    _, tid = await _trad(storage)
    utfall, _, _ = await _svara(storage, tid, "Hej, kan ni visa en demo?", "fraga")
    assert utfall["queued"] and await storage.get_pending_outreach_message(TENANT, tid)


async def test_oppnad_avregistrering_sparrar_adressen_anda():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    utfall, _, _ = await _svara(storage, tid, "Ta bort mig från er lista.", "avregistrering", utan_utkast=True)
    assert utfall["suppressed"]
    assert "tomas@buddy.se" in await storage.list_suppressions(TENANT)
    assert (await storage.get_prospect(TENANT, pid))["status"] == "suppressed"


async def test_inkorgen_skickar_flaggan_vidare_till_svarshanteringen(monkeypatch):
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    mail = await storage.save_email(
        TENANT, provider="imap", provider_message_id="svar-1", from_email="tomas@buddy.se", from_name="Tomas",
        subject="Re: En tanke", body_text="Hej, kan ni visa en demo?", last_i_brevladan=True,
    )
    fangat: dict = {}

    async def svarshantering(storage_, tenant_id, **kwargs):
        fangat.update(kwargs)
        return {"klass": "fraga"}

    monkeypatch.setattr("app.leads.svar.hantera_prospektsvar", svarshantering)
    monkeypatch.setattr(type(processor.get_settings()), "is_simulation", lambda self: False)

    utfall = await process_email(storage, TENANT, mail)

    assert utfall["action"] == "lead" and utfall["thread_id"] == tid
    assert fangat["utan_utkast"] is True and fangat["thread_id"] == tid
    assert (await storage.get_email(TENANT, mail["id"]))["status"] == "lead"
