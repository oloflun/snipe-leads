"""Hämtningen efter UID och mejl som redan var öppnade (migration 150).

Antons beställning 2026-11-23: "Bygg om hämtningen, men se till att supporten
ser de vi öppnat och därmed inte skriver utkast på dem utan sorterar till
manuell hantering." Förtydligat samma dag: "I en fortlöpande konversation som
skötts av Iris eller som är tänkt att skötas av Iris, får inte konversationen
avbrytas eller tappas för att man råkar öppna mailet, alla öppnade mail
behöver kvalificeras och finns det inget svar så bör ett utkast ändå skrivas
och notifiera användaren, ifall det tex glömts bort."

Sökningen på olästa (UNSEEN) tappade varje mejl som en människa hann öppna i
brevlådan före synken. Nu ska

  1. allt med högre UID än brevlådans märke hämtas, läst eller inte;
  2. en brevlåda utan märke börja med olästa plus de senaste dagarna;
  3. märket bara flyttas förbi det som står i databasen;
  4. ett mejl som var öppnat men obesvarat (`last_i_brevladan`) kvalificeras
     och få utkast som vanligt, med en notis som säger att det ligger
     obesvarat, men aldrig skickas av sig självt;
  5. ett mejl som redan var besvarat från brevlådan (`besvarat_i_brevladan`)
     inte få något utkast: Att hantera, avbockat (support), eller överlämnat
     i konversationen (leads), och ändå klassas så att en avregistrering gäller.
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
        b"8 9 10",
        {
            b"8": [(b"1 (UID 8 FLAGS (\\Seen) BODY[] {42}", _rfc822("<last@x>")), b")"],
            # Vissa servrar lägger flaggorna efter kroppen.
            b"9": [(b"2 (UID 9 BODY[] {42}", _rfc822("<olast@x>")), b" FLAGS (\\Recent))"],
            b"10": [(b"3 (UID 10 FLAGS (\\Answered \\Seen) BODY[] {42}", _rfc822("<besvarat@x>")), b")"],
        },
    )
    tillstand: dict = {}
    with patch.object(imap.imaplib, "IMAP4_SSL", return_value=client):
        mejl = imap._fetch_sync(
            "imap.gmail.com", "a@example.com", "pw", "INBOX",
            efter_uid=7, uidvalidity=3, tillbakablick_dagar=7, tillstand=tillstand,
        )

    assert client.sokningar == [("UID", "8:*")]
    assert [(m.imap_uid, m.last_i_brevladan, m.besvarat_i_brevladan) for m in mejl] == [
        ("8", True, False), ("9", False, False), ("10", True, True),
    ]
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


# -- Kundtjänsten -------------------------------------------------------------

PAKETFRAGAN = (
    "Beställde för en vecka sedan och spårningen har inte "
    "uppdaterats på fyra dagar. När kommer paketet?"
)


async def test_besvarat_supportmejl_gar_till_att_hantera_avbockat_utan_utkast(monkeypatch):
    storage = MemoryStorage()
    mail = await storage.save_email(
        DEFAULT_TENANT_ID, provider="imap", provider_message_id="besvarat-1", from_email="anna@example.com",
        from_name="Anna Andersson", subject="Fråga om min order", body_text="Hej, var är mitt paket?",
        last_i_brevladan=True, besvarat_i_brevladan=True,
    )

    async def ingen_modell(*args, **kwargs):
        raise AssertionError("Triagen nåddes fast mejlet redan var besvarat från brevlådan")

    monkeypatch.setattr(processor, "_triage_email", ingen_modell)

    assert await process_email(storage, DEFAULT_TENANT_ID, mail) == {"action": "att_hantera"}

    sparat = await storage.get_email(DEFAULT_TENANT_ID, mail["id"])
    assert sparat["status"] == "att_hantera" and sparat["besvarat_i_brevladan"] and not sparat["draft"]
    # Avbockat: det syns i Att hantera men väntar inte på någon.
    assert sparat["hanterad_at"]
    assert "besvarat_i_brevladan" in [b["event"] for b in await storage.list_decisions(DEFAULT_TENANT_ID, mail["id"])]
    assert [e["id"] for e in await storage.list_emails(DEFAULT_TENANT_ID, status="att_hantera")] == [mail["id"]]
    assert await storage.list_emails(DEFAULT_TENANT_ID) == []


async def _genom_kedjan(*, last: bool) -> dict:
    """Paketfrågan genom hela supportkedjan, med regeln 'auto' för facket."""
    from httpx import ASGITransport, AsyncClient

    from app.config import get_settings
    from app.main import app

    demo = {"X-API-Key": get_settings().snajp_demo_api_key}
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put("/api/rules", headers=demo, json={"category": "leverans", "mode": "auto"})
            storage = app.state.storage
            mail = await storage.save_email(
                DEFAULT_TENANT_ID, provider="imap", provider_message_id=f"paket-{last}",
                from_email="johan@example.com", from_name="Johan Berg", subject="Var är mitt paket?",
                body_text=PAKETFRAGAN, last_i_brevladan=last,
            )
            await process_email(storage, DEFAULT_TENANT_ID, mail)
            return (await client.get(f"/api/inbox/{mail['id']}", headers=demo)).json()


async def test_oppnat_men_obesvarat_supportmejl_far_utkast_men_aldrig_autosvar():
    """Att någon råkat öppna mejlet får inte göra att det tappas: det får sitt
    utkast. Men den som öppnade det kan vara på väg att svara, så det som
    annars hade gått ut av sig självt väntar på ett ja."""
    mejl = await _genom_kedjan(last=True)

    assert mejl["status"] == "awaiting_approval" and mejl["last_i_brevladan"]
    assert mejl["draft"] and mejl["draft"]["status"] == "pending"
    assert processor.AI_UPPLYSNING["sv"] not in mejl["draft"]["content"]
    beslut = {d["event"]: d["detail"] for d in mejl["decisions"]}
    assert "last_i_brevladan" in beslut and "auto_sent" not in beslut
    assert beslut["draft_created"]["why_not_auto"] == "Mejlet var redan öppnat i brevlådan"


async def test_samma_mejl_oppnat_av_ingen_gar_ut_som_autosvar():
    mejl = await _genom_kedjan(last=False)
    assert mejl["status"] == "auto_sent"


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


async def test_oppnat_men_obesvarat_svar_fran_lead_far_utkast_och_en_notis_som_sager_det():
    """Iris konversation får inte tappas för att någon råkat öppna svaret."""
    storage = MemoryStorage()
    pid, tid = await _trad(storage)

    utfall, _, _ = await _svara(storage, tid, "Hej, kan ni visa en demo?", "fraga", oppnat=True)

    assert utfall["klass"] == "fraga" and utfall["queued"] and not utfall["handoff"]
    assert await storage.get_pending_outreach_message(TENANT, tid)
    assert (await storage.get_prospect(TENANT, pid))["status"] == "replied"
    handelser = {h["typ"]: h for h in await storage.list_handelser(TENANT, thread_id=tid)}
    assert handelser["svar"]["detalj"]["last_i_brevladan"] is True
    # Utkastets notis bär märket, så att rubriken blir "Obesvarat i brevlådan".
    assert handelser["utkast"]["detalj"]["oppnat"] is True and handelser["utkast"]["notis"]
    assert "overlamnat" not in handelser
    notiser = await storage.list_notiser(TENANT)
    assert any(n["typ"] == "utkast" and (n.get("detalj") or {}).get("oppnat") for n in notiser)


async def test_svar_oppnat_av_ingen_far_utkast_utan_market():
    storage = MemoryStorage()
    _, tid = await _trad(storage)
    utfall, _, _ = await _svara(storage, tid, "Hej, kan ni visa en demo?", "fraga")
    assert utfall["queued"] and await storage.get_pending_outreach_message(TENANT, tid)
    handelser = {h["typ"]: h for h in await storage.list_handelser(TENANT, thread_id=tid)}
    assert "oppnat" not in handelser["utkast"]["detalj"] and "last_i_brevladan" not in handelser["svar"]["detalj"]


async def test_redan_besvarat_svar_fran_lead_sparas_och_klassas_men_far_inget_utkast():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)

    utfall, _, mejl = await _svara(
        storage, tid, "Hej, kan ni visa en demo?", "fraga", oppnat=True, utan_utkast=True
    )

    assert utfall["klass"] == "fraga" and not utfall["queued"] and utfall["handoff"]
    assert utfall["eskalerat"] == ["besvarat_i_brevladan"]
    assert await storage.get_pending_outreach_message(TENANT, tid) is None
    # Svaret står i tråden och leadet har flyttats till Svarat.
    assert [m["direction"] for m in await storage.list_outreach_messages(TENANT, tid)] == ["outbound", "inbound"]
    assert (await storage.get_prospect(TENANT, pid))["status"] == "replied"
    # Konversationen säger varför det inte finns något utkast.
    handelser = {h["typ"]: h for h in await storage.list_handelser(TENANT, thread_id=tid)}
    assert handelser["svar"]["detalj"]["besvarat_i_brevladan"] is True
    assert handelser["overlamnat"]["detalj"]["eskalerat"] == ["besvarat_i_brevladan"]
    assert "utkast" not in handelser
    # Den som svarade vet redan om det: inget prioriterat mejl.
    mejl.assert_not_called()


async def test_besvarad_avregistrering_sparrar_adressen_anda():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    utfall, _, _ = await _svara(
        storage, tid, "Ta bort mig från er lista.", "avregistrering", oppnat=True, utan_utkast=True
    )
    assert utfall["suppressed"]
    assert "tomas@buddy.se" in await storage.list_suppressions(TENANT)
    assert (await storage.get_prospect(TENANT, pid))["status"] == "suppressed"


@pytest.mark.parametrize(
    ("besvarat", "vantat"), [(False, {"oppnat": True, "utan_utkast": False}), (True, {"oppnat": True, "utan_utkast": True})]
)
async def test_inkorgen_skickar_flaggorna_vidare_till_svarshanteringen(monkeypatch, besvarat, vantat):
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    mail = await storage.save_email(
        TENANT, provider="imap", provider_message_id="svar-1", from_email="tomas@buddy.se", from_name="Tomas",
        subject="Re: En tanke", body_text="Hej, kan ni visa en demo?",
        last_i_brevladan=True, besvarat_i_brevladan=besvarat,
    )
    fangat: dict = {}

    async def svarshantering(storage_, tenant_id, **kwargs):
        fangat.update(kwargs)
        return {"klass": "fraga"}

    monkeypatch.setattr("app.leads.svar.hantera_prospektsvar", svarshantering)
    monkeypatch.setattr(type(processor.get_settings()), "is_simulation", lambda self: False)

    utfall = await process_email(storage, TENANT, mail)

    assert utfall["action"] == "lead" and utfall["thread_id"] == tid
    assert {k: fangat[k] for k in vantat} == vantat and fangat["thread_id"] == tid
    assert (await storage.get_email(TENANT, mail["id"]))["status"] == "lead"
