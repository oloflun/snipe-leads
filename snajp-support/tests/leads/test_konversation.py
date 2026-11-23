"""Iris-konversationerna (app/leads/konversation.py, migration 149): steget,
påstådda handlingar, mejl utanför Snajp ur citaten och händelserna när ett
svar kommer in. Mot MemoryStorage; run_step mockas som i test_svar.py."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.leads import konversation, samtal
from app.leads.svar import hantera_prospektsvar
from app.storage.memory import MemoryStorage

from .test_svar import _stegsvar

TENANT = "00000000-0000-4000-a000-000000000001"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Påstådda handlingar ------------------------------------------------------


def test_utkast_som_pastar_en_handling_flaggas():
    text = "Hej Tomas,\n\nTack! Jag har skickat en inbjudan till måndag kl 10. Hör av dig om tiden inte passar."
    assert konversation.handlingspastaenden(text) == ["Jag har skickat en inbjudan till måndag kl 10"]
    assert konversation.handlingspastaenden("Perfekt, har skickat en inbjudan till dig!") == [
        "har skickat en inbjudan till dig"
    ]
    assert konversation.handlingspastaenden("I've attached the price list.") == ["I've attached the price list"]


def test_ett_vanligt_svar_flaggas_inte():
    text = "Hej Tomas,\n\nVad roligt! Passar måndag efter kl 10? Då skickar jag en inbjudan."
    assert konversation.handlingspastaenden(text) == []


# -- Steget -------------------------------------------------------------------


def test_steget_foljer_status_och_manuellt_val():
    assert konversation.steg({"status": "meeting"}) == "mote"
    assert konversation.steg({"status": "won"}) == "mote"
    assert konversation.steg({"status": "lost"}) == "ej_intresserad"
    assert konversation.steg({"status": "suppressed"}) == "kontakta_inte"
    assert konversation.steg({"status": "replied", "svarsklass": "aterkom"}) == "aterkom"
    assert konversation.steg({"status": "replied", "aterkom_datum": "2026-12-01"}) == "aterkom"
    # En människa som sagt Svarat går före Iris klassning.
    assert konversation.steg({"status": "replied", "svarsklass": "aterkom", "steg": "svarat"}) == "svarat"
    assert konversation.steg({"status": "replied"}) == "svarat"


def test_att_gora():
    idag = date(2026, 11, 22)
    assert konversation.att_gora({"status": "replied", "olasta": 1}, idag)
    assert konversation.att_gora({"status": "replied", "utkast_id": "x"}, idag)
    assert konversation.att_gora({"status": "replied", "aterkom_datum": "2026-11-22"}, idag)
    assert not konversation.att_gora({"status": "replied", "aterkom_datum": "2026-11-30"}, idag)
    assert not konversation.att_gora({"status": "lost", "utkast_id": "x"}, idag)


# -- Mejl utanför Snajp ur citaten --------------------------------------------

VART_MEJL = (
    "Hej Tomas,\n\nJag undrar om mitt förra mejl hann fram. Det handlade om hur ni enklare kan "
    "hantera miljontals konversationer."
)

HENRIKS_SVAR = """Toppen!

Hälsningar
Henrik

18 nov. 2026 kl. 12:56 skrev Sebastian Bergman <sebastian@snajp.se>:

> Perfekt, har skickat en inbjudan till dig!
>
> Allt gott!
> Hälsningar, Sebastian
>
> 17 nov. 2026 kl. 13:00 skrev Henrik Jalvin <henrik.jalvin@buddy.se>:
>
>> Hej, inga problem. Måndag är dugligt efter kl 10.
>>
>> 12 nov. 2026 kl. 08:13 skrev Snajp <snajpsupport@gmail.com>:
>>
>>> Hej Tomas,
>>>
>>> Jag undrar om mitt förra mejl hann fram. Det handlade om hur ni enklare kan
>>> hantera miljontals konversationer.
"""


def _meddelanden():
    return [
        {"id": "u1", "direction": "outbound", "body": VART_MEJL, "sent_at": "2026-11-12T07:13:00+00:00"},
        {"id": "i1", "direction": "inbound", "body": "Hej, inga problem. Måndag är dugligt efter kl 10.",
         "sent_at": "2026-11-17T12:00:00+00:00"},
        {"id": "i2", "direction": "inbound", "body": HENRIKS_SVAR, "sent_at": "2026-11-18T12:10:00+00:00"},
        # Samma citat i nästa svar ger inte ett andra mejl.
        {"id": "i3", "direction": "inbound", "body": "Tack igen!\n\n" + HENRIKS_SVAR.split("Henrik\n\n", 1)[1],
         "sent_at": "2026-11-18T13:00:00+00:00"},
    ]


def test_sebastians_gmailsvar_syns_ur_citatet():
    externa = konversation.externa_ur_citat(_meddelanden(), prospekt_epost="tomas@buddy.se")
    assert len(externa) == 1
    mejl = externa[0]
    assert mejl["avsandare"] == "sebastian@snajp.se"
    assert mejl["text"].startswith("Perfekt, har skickat en inbjudan till dig!")
    assert "Henrik Jalvin" not in mejl["text"]  # nästa citat ingår inte
    assert mejl["tid"] == datetime(2026, 11, 18, 11, 56, tzinfo=timezone.utc)
    assert mejl["tid_ur_citat"]


def test_vara_egna_mejl_och_prospektets_kollegor_raknas_inte():
    externa = konversation.externa_ur_citat(_meddelanden(), prospekt_epost="tomas@buddy.se")
    avsandare = {e["avsandare"] for e in externa}
    assert "henrik.jalvin@buddy.se" not in avsandare  # samma domän som prospektet
    assert "snajpsupport@gmail.com" not in avsandare  # vårt eget utskick, citerat


def test_forslag_om_mote_ur_texten():
    assert konversation.ser_ut_som_bokat_mote(["Perfekt, har skickat en inbjudan till dig!"])
    assert not konversation.ser_ut_som_bokat_mote(["Kan vi ta det nästa vecka?"])


# -- Händelserna när svar kommer in -------------------------------------------


async def _trad(storage) -> tuple[str, str]:
    prospekt = await storage.create_prospect(TENANT, company_name="Telecom Buddy AB", contact_email="tomas@buddy.se")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=prospekt["id"])
    koat = await storage.queue_outreach_message(
        TENANT, thread_id=trad["id"], body=VART_MEJL, subject="En tanke", humanizer_variant="snajp:humanizer-svenska",
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    await storage.mark_outreach_message_sent(TENANT, koat["message"]["id"], datetime.now(timezone.utc) - timedelta(days=5))
    await storage.update_send_queue_status(TENANT, koat["queue_item"]["id"], status="sent", gate_checks={})
    await storage.update_prospect(TENANT, prospekt["id"], status="contacted")
    return prospekt["id"], trad["id"]


async def _svara(storage, thread_id, body):
    steg, _ = _stegsvar({
        "sa:call-summary": {"klass": "fraga", "fraga_karna": "När passar ett möte?"},
        "mk:sales-enablement": {"subject": "Re: demo", "body": "Hej Tomas, passar måndag kl 10?"},
        "snajp:humanizer-svenska": {"final_subject": "Re: demo", "final_body": "Hej Tomas, passar måndag kl 10?"},
    })
    with patch("app.leads.svar.run_step", new=steg), patch(
        "app.leads.svar.skicka_prioriterat", new=AsyncMock(return_value=True)
    ):
        return await hantera_prospektsvar(
            storage, TENANT, thread_id=thread_id, body=body, tenant_name="Snajp",
            context_pack="## Kontextpaket\nSnajp säljer AI-support. Möte måndag kl 10 demo.",
        )


async def test_nytt_svar_ger_notis_utkast_och_synlig_ersattning():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    await storage.satt_trad_steg(TENANT, tid, steg="svarat", aterkom_datum=None)

    forsta = await _svara(storage, tid, "Hej, kan ni visa en demo?")
    assert forsta["queued"], forsta
    forsta_utkast = await storage.get_pending_outreach_message(TENANT, tid)
    andra = await _svara(storage, tid, "Måndag efter kl 10 funkar.")
    assert andra["queued"], andra

    typer = [h["typ"] for h in await storage.list_handelser(TENANT, thread_id=tid)]
    assert typer.count("svar") == 2 and typer.count("utkast") == 2 and typer.count("klassad") == 2
    assert "utkast_ersatt" in typer
    # Det ersatta utkastet finns kvar, kasserat, och går att återställa.
    gamla = next(m for m in await storage.list_outreach_messages(TENANT, tid) if m["id"] == forsta_utkast["id"])
    assert gamla["kasserad_at"]
    assert await storage.aterstall_utkast(TENANT, tid, forsta_utkast["id"])
    # Ett nytt svar nollar det manuella steget.
    assert (await storage.get_outreach_thread(TENANT, tid)).get("steg") is None
    assert await storage.antal_olasta_notiser(TENANT) == 4  # två svar, två utkast


async def test_mote_bokat_flyttar_status_kasserar_utkastet_och_ger_notis():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    await _svara(storage, tid, "Hej, kan ni visa en demo?")
    await storage.markera_notiser_lasta(TENANT)
    trad = await storage.get_outreach_thread(TENANT, tid)
    prospekt = await storage.get_prospect(TENANT, pid)

    ut = await konversation.satt_steg(storage, TENANT, thread=trad, prospect=prospekt, nytt="mote")

    assert ut["kasserat"]
    assert (await storage.get_prospect(TENANT, pid))["status"] == "meeting"
    assert await storage.get_pending_outreach_message(TENANT, tid) is None
    handelser = await storage.list_handelser(TENANT, thread_id=tid)
    mote = [h for h in handelser if h["typ"] == "mote"]
    assert len(mote) == 1 and mote[0]["notis"] and mote[0]["last_at"]  # den som bokade har sett det
    assert konversation.steg({**await storage.get_outreach_thread(TENANT, tid), "status": "meeting"}) == "mote"


async def test_aterkom_kraver_datum_och_star_i_aterkopplingen():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    await storage.update_prospect(TENANT, pid, status="replied")
    trad = await storage.get_outreach_thread(TENANT, tid)
    prospekt = await storage.get_prospect(TENANT, pid)
    with pytest.raises(ValueError):
        await konversation.satt_steg(storage, TENANT, thread=trad, prospect=prospekt, nytt="aterkom")
    await konversation.satt_steg(
        storage, TENANT, thread=trad, prospect=prospekt, nytt="aterkom", aterkom_datum=date(2026, 11, 25)
    )
    await storage.update_prospect(TENANT, pid, contact_email="tomas@buddy.se")
    prospekter = [{**await storage.get_prospect(TENANT, pid), "contact_phone": "0313000401"}]
    aterkom = await storage.aterkom_datum(TENANT)
    fore = samtal.samtalslista(prospekter, [], {}, lista="aterkoppling", idag=date(2026, 11, 24), aterkom=aterkom)
    pa_dagen = samtal.samtalslista(prospekter, [], {}, lista="aterkoppling", idag=date(2026, 11, 25), aterkom=aterkom)
    assert fore[0]["ring_idag"] is False and fore[0]["nasta"] == "2026-11-25"
    assert pa_dagen[0]["ring_idag"] is True


# -- Återkontakten (Anton 2026-11-23) -----------------------------------------


def test_aterkontaktens_datum():
    regler = konversation.aterkontakt_regler(None)
    idag = date(2026, 11, 23)
    assert regler == {"nej_manader": 6, "aterkom_manader": 2}
    assert konversation.aterkontakt_datum("negativt", idag=idag, regler=regler) == date(2027, 5, 23)
    assert konversation.aterkontakt_datum("aterkom", idag=idag, regler=regler) == date(2027, 1, 23)
    # Tiden de själva nämnde går före, men bara framåt i tiden och inom två år.
    assert konversation.aterkontakt_datum("aterkom", idag=idag, regler=regler, namngivet="2027-03-01") == date(2027, 3, 1)
    assert konversation.aterkontakt_datum("aterkom", idag=idag, regler=regler, namngivet="2020-03-01") == date(2027, 1, 23)
    assert konversation.aterkontakt_datum("aterkom", idag=idag, regler=regler, namngivet="inte ett datum") == date(2027, 1, 23)
    assert konversation.aterkontakt_datum("avregistrering", idag=idag, regler=regler) is None
    # Kundval: 0 stänger av, och den 31:a blir månadens sista dag.
    assert konversation.aterkontakt_datum("negativt", idag=idag, regler={"nej_manader": 0, "aterkom_manader": 2}) is None
    assert konversation.plus_manader(date(2026, 8, 31), 6) == date(2027, 2, 28)
    assert konversation.aterkontakt_regler({"aterkontakt": {"nej_manader": 4}})["nej_manader"] == 4


def test_ett_nej_med_passerat_datum_ar_att_gora():
    idag = date(2027, 5, 23)
    assert konversation.att_gora({"status": "lost", "aterkom_datum": "2027-05-23"}, idag)
    assert not konversation.att_gora({"status": "lost", "aterkom_datum": "2027-06-01"}, idag)
    assert not konversation.att_gora({"status": "suppressed", "aterkom_datum": "2027-05-01"}, idag)


async def _klassa(storage, thread_id, body, klassning):
    steg, _ = _stegsvar({"sa:call-summary": klassning})
    with patch("app.leads.svar.run_step", new=steg), patch(
        "app.leads.svar.skicka_prioriterat", new=AsyncMock(return_value=True)
    ):
        return await hantera_prospektsvar(
            storage, TENANT, thread_id=thread_id, body=body, tenant_name="Snajp", context_pack="## Kontextpaket\nSnajp.",
        )


async def test_ett_nej_sparrar_inte_men_det_andra_gor_det():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)

    forsta = await _klassa(storage, tid, "Nej tack, inte intresserade.", {"klass": "negativt"})
    assert forsta["suppressed"] is False and forsta["andra_nej"] is False
    assert (await storage.get_prospect(TENANT, pid))["status"] == "lost"
    assert "tomas@buddy.se" not in await storage.list_suppressions(TENANT)
    trad = await storage.get_outreach_thread(TENANT, tid)
    assert trad["aterkom_datum"] == forsta["aterkontakt"]
    assert date.fromisoformat(trad["aterkom_datum"]) == konversation.plus_manader(datetime.now(timezone.utc).date(), 6)

    # Två nej i rad på samma mejl är ett nej: ingen spärr utan en återkontakt emellan.
    igen = await _klassa(storage, tid, "Nej, som sagt.", {"klass": "negativt"})
    assert igen["andra_nej"] is False and igen["suppressed"] is False

    # Återkontakten går ut, och de tackar nej igen: Kontakta inte.
    koat = await storage.queue_outreach_message(
        TENANT, thread_id=tid, body="Har läget ändrats?", subject="Hej igen", humanizer_variant="v",
        scheduled_at=datetime.now(timezone.utc),
    )
    await storage.mark_outreach_message_sent(TENANT, koat["message"]["id"], datetime.now(timezone.utc) + timedelta(seconds=1))
    await storage.update_send_queue_status(TENANT, koat["queue_item"]["id"], status="sent", gate_checks={})
    andra = await _klassa(storage, tid, "Nej tack.", {"klass": "negativt"})
    assert andra["andra_nej"] is True and andra["suppressed"] is True and andra["aterkontakt"] is None
    assert (await storage.get_prospect(TENANT, pid))["status"] == "suppressed"
    assert "tomas@buddy.se" in await storage.list_suppressions(TENANT)
    assert (await storage.get_outreach_thread(TENANT, tid))["aterkom_datum"] is None


async def test_aterkom_far_tiden_de_namner_och_en_avregistrering_inget_datum():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    om_tre = konversation.plus_manader(datetime.now(timezone.utc).date(), 3)
    svar = await _klassa(storage, tid, "Hör av er längre fram.", {"klass": "aterkom", "aterkom_datum": om_tre.isoformat()})
    assert svar["aterkontakt"] == om_tre.isoformat()
    assert (await storage.get_prospect(TENANT, pid))["status"] == "replied"
    assert konversation.steg({**await storage.get_outreach_thread(TENANT, tid), "status": "replied"}) == "aterkom"

    avreg = await _klassa(storage, tid, "Kontakta oss inte igen.", {"klass": "avregistrering"})
    assert avreg["suppressed"] is True and avreg["aterkontakt"] is None
    assert (await storage.get_outreach_thread(TENANT, tid))["aterkom_datum"] is None


async def test_manuellt_ej_intresserad_far_sex_manader():
    storage = MemoryStorage()
    pid, tid = await _trad(storage)
    ut = await konversation.satt_steg(
        storage, TENANT, thread=await storage.get_outreach_thread(TENANT, tid),
        prospect=await storage.get_prospect(TENANT, pid), nytt="ej_intresserad",
    )
    assert ut["aterkom_datum"] == konversation.plus_manader(datetime.now(timezone.utc).date(), 6).isoformat()
    inte = await konversation.satt_steg(
        storage, TENANT, thread=await storage.get_outreach_thread(TENANT, tid),
        prospect=await storage.get_prospect(TENANT, pid), nytt="kontakta_inte",
    )
    assert inte["aterkom_datum"] is None and "tomas@buddy.se" in await storage.list_suppressions(TENANT)


async def test_generering_overlever_omladdning():
    nu = datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc)
    startad = {"typ": "generering_startad", "created_at": (nu - timedelta(minutes=1)).isoformat()}
    assert konversation.generering([startad], nu=nu)["pagar"]
    fel = {"typ": "generering_fel", "created_at": nu.isoformat(), "detalj": {"fel": "Stoppat"}}
    assert konversation.generering([startad, fel], nu=nu) == {"pagar": False, "fel": "Stoppat", "startad_at": startad["created_at"]}
    gammal = {"typ": "generering_startad", "created_at": (nu - timedelta(minutes=30)).isoformat()}
    assert not konversation.generering([gammal], nu=nu)["pagar"]
