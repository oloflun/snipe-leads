"""CRM-flödet för leads (Antons beställning 2026-10-07, Fas 2–4).

En sanning per lead om utkastet, avslutade och arkiverade leads som aldrig
får mejl, 90-dagarsspärren som inte längre fäller samtalets egen
uppföljning, och bevakningen som bara skriver utkast till granskning — och
aldrig följer upp produktionens trådar från en spegel.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.leads import scheduler, utkaststatus
from app.leads.follow_up_generator import generate_due_follow_ups, skickad_efter_spegling
from app.leads.scheduler import process_due_item
from app.storage.memory import MemoryStorage
from tests.leads.test_follow_up_generator import NU, _skickad_trad, _stegsvar
from tests.leads.test_follow_up_generator import TENANT as UPPF_TENANT
from tests.leads.test_scheduler import GODKAND_BRODTEXT, TENANT, WITHIN_WINDOW_UTC, _FakeSendProvider, _seed

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Utkaststatusen, ren härledning -----------------------------------------


def _lage(**over):
    grund = {"prospect_id": "p", "thread_id": "t", "skickat_at": None, "antal_skickade": 0,
             "queue_item_id": "q", "ko_status": None, "gate_checks": {}, "scheduled_at": None}
    grund.update(over)
    return grund


@pytest.mark.parametrize(
    ("lage", "status"),
    [
        (None, "saknas"),
        (_lage(queue_item_id=None), "saknas"),
        (_lage(ko_status="awaiting_review"), "vantar"),
        (_lage(ko_status="queued", gate_checks={"approved_by": "human"}), "godkant"),
        (_lage(ko_status="queued", gate_checks={}), "koad"),
        (_lage(ko_status="sent", skickat_at="2026-10-07T09:00:00+00:00", antal_skickade=1), "skickat"),
        (_lage(ko_status="cancelled"), "avvisat"),
        (_lage(ko_status="blocked", gate_checks={"send_guard_skal": "Klockan är 03:14."}), "stoppat"),
        # Ett aktivt nästa steg går före "skickat"; skickat går före avvisat.
        (_lage(ko_status="awaiting_review", skickat_at="2026-10-01T09:00:00+00:00"), "vantar"),
        (_lage(ko_status="cancelled", skickat_at="2026-10-01T09:00:00+00:00"), "skickat"),
    ],
)
def test_varje_utkaststatus_harleds(lage, status):
    assert utkaststatus.harled(lage)["utkast_status"] == status


def test_stoppat_bar_skalet_och_godkant_bar_nasta_sandtid():
    stopp = utkaststatus.harled(_lage(ko_status="blocked", gate_checks='{"send_guard_skal": "Avregistrerad."}'))
    assert stopp["utkast_skal"] == "Avregistrerad." and stopp["queue_item_id"] is None
    # Godkänt onsdag 16:41 svensk tid (14:41 UTC) går ut torsdag 08:00.
    onsdag_kvall = datetime(2026, 10, 7, 14, 41, tzinfo=timezone.utc)
    godkant = utkaststatus.harled(
        _lage(ko_status="queued", gate_checks={"approved_by": "human"}, scheduled_at=onsdag_kvall.isoformat()),
        now=onsdag_kvall + timedelta(hours=4),
    )
    assert godkant["queue_item_id"] == "q"
    assert godkant["skickas_tidigast"] == "2026-10-08T08:00:00+02:00"


def test_nasta_sandtid_hoppar_over_helgen():
    fredag_kvall = datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc)
    assert utkaststatus.nasta_sandtid(None, now=fredag_kvall) == "2026-10-12T08:00:00+02:00"


async def test_utkast_lagen_valjer_det_vantande_utkastet_och_senaste_koposten():
    storage = MemoryStorage()
    p = await storage.create_prospect(TENANT, company_name="Bolaget AB")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=p["id"])
    forsta = await storage.queue_outreach_message(
        TENANT, thread_id=trad["id"], body="gammalt", subject="A", humanizer_variant="v",
        scheduled_at=WITHIN_WINDOW_UTC, status="awaiting_review",
    )
    await storage.cancel_pending_sends(TENANT, trad["id"])
    andra = await storage.queue_outreach_message(
        TENANT, thread_id=trad["id"], body="nytt", subject="B", humanizer_variant="v",
        scheduled_at=WITHIN_WINDOW_UTC, status="awaiting_review",
    )
    lage = (await storage.utkast_lagen(TENANT, med_text=True))[p["id"]]
    assert lage["body"] == "nytt" and lage["queue_item_id"] == andra["queue_item"]["id"]
    assert utkaststatus.harled(lage)["utkast_status"] == "vantar"
    assert forsta["queue_item"]["status"] == "cancelled"


# -- send_guard: avslutade och arkiverade leads får inget mejl ---------------


async def _med_prospekt(storage: MemoryStorage, **prospekt) -> tuple[str, str, str]:
    item_id, thread_id, message_id = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    p = await storage.create_prospect(TENANT, company_name="Kund AB", contact_email="vd@kund.se", origin="manual")
    p.update(prospekt)
    storage.outreach_threads[TENANT][thread_id]["prospect_id"] = p["id"]
    return item_id, thread_id, p["id"]


@pytest.mark.parametrize("andring", [{"status": "lost"}, {"status": "suppressed"}, {"arkiverad_at": "2026-10-08T10:00:00+00:00"}])
async def test_utskick_stoppas_for_avslutat_eller_arkiverat_lead(andring):
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, thread_id, _ = await _med_prospekt(storage, **andring)
    godkant = {"approved_by": "human", "via": "granskningskön", "godkand_at": WITHIN_WINDOW_UTC.isoformat()}
    utfall = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC, godkant=godkant
    )
    assert utfall == "blocked" and provider.sent == []
    post = next(i for i in storage.send_queue[TENANT] if i["id"] == item_id)
    assert post["gate_checks"]["send_guard_regel"] in ("arkiverad", "avslutad")


async def test_aktivt_lead_skickas_som_vanligt():
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, thread_id, _ = await _med_prospekt(storage)
    utfall = await process_due_item(storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC)
    assert utfall == "sent" and provider.sent[0]["body"] == GODKAND_BRODTEXT


# -- 90-dagarsspärren räknar inte leadets egen tråd --------------------------


def _skickat_i(storage: MemoryStorage, thread_id: str, nyckel: str, dagar_sedan: int) -> None:
    storage.outreach_messages[TENANT].append({
        "id": f"m-{thread_id}-{dagar_sedan}", "thread_id": thread_id, "direction": "outbound",
        "sent_at": WITHIN_WINDOW_UTC - timedelta(days=dagar_sedan), "body": "", "subject": "",
        "humanizer_variant": "snajp:humanizer-svenska", "foretagsnyckel": nyckel,
    })


async def test_uppfoljning_i_samma_trad_fastnar_inte_i_90_dagarssparren():
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, thread_id, message_id = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    storage.outreach_threads[TENANT][thread_id]["foretagsnyckel"] = "5560001111"
    _skickat_i(storage, thread_id, "5560001111", dagar_sedan=10)

    assert await storage.last_contact_with_company(TENANT, "5560001111", utom_trad=thread_id) is None
    # Uppföljningen är godkänd av en människa (autonomin håller annars kvar steg 2).
    godkant = {"approved_by": "human", "via": "granskningskön", "godkand_at": WITHIN_WINDOW_UTC.isoformat()}
    utfall = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC, godkant=godkant
    )
    assert utfall == "sent"


async def test_annan_trad_till_samma_bolag_sparras_fortfarande():
    storage, provider = MemoryStorage(), _FakeSendProvider()
    item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    storage.outreach_threads[TENANT][thread_id]["foretagsnyckel"] = "5560001111"
    _skickat_i(storage, "en-annan-trad", "5560001111", dagar_sedan=10)

    utfall = await process_due_item(storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC)
    assert utfall == "blocked" and provider.sent == []
    post = next(i for i in storage.send_queue[TENANT] if i["id"] == item_id)
    assert post["gate_checks"]["send_guard_regel"] == "5_volymtak"


# -- Trådaggregaten ----------------------------------------------------------


async def test_tradaggregaten_raknar_varje_mejl_en_gang_och_ignorerar_kasserade():
    storage = MemoryStorage()
    p = await storage.create_prospect(TENANT, company_name="Räknebolaget AB")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=p["id"])
    for _ in range(2):
        koat = await storage.queue_outreach_message(
            TENANT, thread_id=trad["id"], body="x", subject="s", humanizer_variant="v",
            scheduled_at=WITHIN_WINDOW_UTC,
        )
        await storage.mark_outreach_message_sent(TENANT, koat["message"]["id"], WITHIN_WINDOW_UTC)
        await storage.update_send_queue_status(TENANT, koat["queue_item"]["id"], status="sent", gate_checks={})
    await storage.queue_outreach_message(
        TENANT, thread_id=trad["id"], body="avvisas", subject="s", humanizer_variant="v",
        scheduled_at=WITHIN_WINDOW_UTC, status="awaiting_review",
    )
    await storage.cancel_pending_sends(TENANT, trad["id"])

    rad = next(t for t in await storage.list_outreach_threads(TENANT) if t["id"] == trad["id"])
    # Två köposter och två mejl: en join utan distinct hade räknat fyra.
    assert rad["outbound_sent_count"] == 2
    assert rad["has_pending_item"] is False, "Ett kasserat utkast är inget nästa steg."
    assert rad["first_outbound_sent_at"] == WITHIN_WINDOW_UTC


# -- Bevakningen: bara utkast till granskning, aldrig produktionens trådar ---


async def test_uppfoljning_blir_granskningsutkast_aven_pa_hogsta_autonomin(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("SEND_QUEUE_POLL_SECONDS", "60")
    get_settings.cache_clear()
    storage = MemoryStorage()
    storage.agent_settings[(UPPF_TENANT, "leads")] = {"autonomy": "auto_send"}
    thread_id = await _skickad_trad(storage)
    with patch("app.leads.follow_up_generator.run_step", new=_stegsvar()):
        rader = await generate_due_follow_ups(
            storage, UPPF_TENANT, now=NU, tenant_name="Snajp", context_pack="## Kontextpaket\nSnajp säljer AI-support."
        )
    assert rader and rader[0]["status"] == "awaiting_review"
    nya = [q for q in storage.send_queue[UPPF_TENANT] if q["thread_id"] == thread_id and q["status"] != "sent"]
    assert [q["status"] for q in nya] == ["awaiting_review"]


async def test_spegeln_foljer_inte_upp_tradar_som_kopierats_fran_produktionen():
    storage = MemoryStorage()
    await _skickad_trad(storage)  # första utskicket NU - 6 dagar
    efter = (NU - timedelta(days=5)).isoformat()  # speglad efter utskicket
    with patch("app.leads.follow_up_generator.run_step", new=_stegsvar()):
        kopierade = await generate_due_follow_ups(
            storage, UPPF_TENANT, now=NU, tenant_name="Snajp", context_pack="x", forst_skickad_efter=efter
        )
        egna = await generate_due_follow_ups(
            storage, UPPF_TENANT, now=NU, tenant_name="Snajp", context_pack="## Kontextpaket\nSnajp säljer AI-support.",
            forst_skickad_efter=(NU - timedelta(days=30)).isoformat(),
        )
    assert kopierade == []
    assert len(egna) == 1


def test_spegelvakten_ar_forsiktig_vid_okand_tid():
    assert skickad_efter_spegling({"first_outbound_sent_at": None}, "2026-10-01T00:00:00+00:00") is False
    assert skickad_efter_spegling({"first_outbound_sent_at": None}, None) is True


async def test_svepet_skickar_seeded_at_vidare_och_hoppar_over_vid_trasig_markor(monkeypatch):
    anrop: list = []

    async def fejk_generera(storage, tenant_id, **kw):
        anrop.append(kw["forst_skickad_efter"])
        return []

    async def fejk_paket(storage, tenant_id):
        return "paket", []

    monkeypatch.setattr(scheduler, "get_settings", lambda: SimpleNamespace(is_simulation=lambda: False))
    monkeypatch.setattr("app.leads.follow_up_generator.generate_due_follow_ups", fejk_generera)
    monkeypatch.setattr("app.leads.context_pack.build_context_pack", fejk_paket)

    storage = MemoryStorage()

    async def spegel():
        return {"environment": "development", "seeded_at": "2026-10-08T02:00:00+00:00"}

    storage.spegel_info = spegel
    await scheduler.sweep_follow_ups(storage)
    assert anrop and set(anrop) == {"2026-10-08T02:00:00+00:00"}

    async def trasig():
        raise RuntimeError("markören gick inte att läsa")

    storage.spegel_info = trasig
    anrop.clear()
    assert await scheduler.sweep_follow_ups(storage) == [] and anrop == []
