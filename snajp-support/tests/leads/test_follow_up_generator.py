"""Uppföljningsgeneratorn: due-policyn som ren funktion, och svepet mot
MemoryStorage med run_step fejkad vid nätverksgränsen."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.leads.follow_up_generator import (
    FOLLOW_UP_DELAYS,
    MAX_OUTBOUND,
    generate_due_follow_ups,
    trad_som_ar_forfallna,
)
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"
NU = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _trad(**over):
    grund = {
        "id": "t-1",
        "outbound_sent_count": 1,
        "last_outbound_sent_at": (NU - timedelta(days=5)).isoformat(),
        "last_inbound_at": None,
        "has_pending_item": False,
        "language_state": "sv",
        "company_name": "Nordiska Verktyg AB",
        "contact_email": "vd@nordiskaverktyg.se",
    }
    grund.update(over)
    return grund


# -- Policyn, ren --------------------------------------------------------


def test_tyst_trad_efter_fyra_dagar_ar_forfallen():
    traffar = trad_som_ar_forfallna([_trad()], now=NU)
    assert [(t["id"], seq) for t, seq in traffar] == [("t-1", 1)]


def test_for_tidigt_ar_inte_forfallet():
    trad = _trad(last_outbound_sent_at=(NU - timedelta(days=2)).isoformat())
    assert trad_som_ar_forfallna([trad], now=NU) == []


def test_svarad_trad_lamnas_at_svarshanteringen():
    trad = _trad(last_inbound_at=(NU - timedelta(days=1)).isoformat())
    assert trad_som_ar_forfallna([trad], now=NU) == []


def test_pending_utkast_sparrar_nasta_steg():
    """Självbegränsningen: ett genererat men ogodkänt utkast gör tråden
    icke-förfallen — generatorn kan inte spamma samma tråd."""
    trad = _trad(has_pending_item=True)
    assert trad_som_ar_forfallna([trad], now=NU) == []


def test_ingen_uppfoljning_utan_skickat_initialmejl():
    trad = _trad(outbound_sent_count=0, last_outbound_sent_at=None)
    assert trad_som_ar_forfallna([trad], now=NU) == []


def test_sekvensen_tar_slut_vid_max():
    trad = _trad(
        outbound_sent_count=MAX_OUTBOUND,
        last_outbound_sent_at=(NU - timedelta(days=30)).isoformat(),
    )
    assert trad_som_ar_forfallna([trad], now=NU) == []


def test_senare_steg_kraver_langre_tystnad():
    """Steg 2 förfaller efter 6 dagar, inte 4 — stigande avstånd."""
    for dagar, forvantat in ((5, []), (7, [("t-1", 2)])):
        trad = _trad(
            outbound_sent_count=2,
            last_outbound_sent_at=(NU - timedelta(days=dagar)).isoformat(),
        )
        assert [
            (t["id"], seq) for t, seq in trad_som_ar_forfallna([trad], now=NU)
        ] == forvantat, f"dagar={dagar}"


def test_delayerna_tacker_hela_sekvensen():
    assert set(FOLLOW_UP_DELAYS) == set(range(1, MAX_OUTBOUND))


# -- Svepet, mot lagring --------------------------------------------------


def _stegsvar():
    from app.agent.step_runner import StepResult

    async def _run_step(step, ledger, trace, *, task, case_context, **kwargs):
        output = {
            "sa:draft-outreach": {
                "subject": "Kort uppföljning",
                "body": "Hej igen! Ville bara höra om du hann fundera.",
            },
            "snajp:humanizer-svenska": {
                "final_subject": "Kort uppföljning",
                "final_body": "Hej igen! Ville bara höra om du hunnit fundera.",
            },
        }.get(step.skill, {})
        ledger.mark_skill_injected(step.skill)
        trace.steps.append(
            StepResult(
                skill=step.skill, output=output, attempts=1, escalated=False,
                escalation_reason=None, latency_ms=1, tokens_in=10, tokens_out=5,
            )
        )
        return output

    return _run_step


async def _skickad_trad(storage) -> str:
    prospect = await storage.create_prospect(
        TENANT, company_name="Nordiska Verktyg AB", contact_email="vd@nordiskaverktyg.se"
    )
    thread = await storage.ensure_outreach_thread(TENANT, prospect_id=prospect["id"])
    resultat = await storage.queue_outreach_message(
        TENANT,
        thread_id=thread["id"],
        body="Första mejlet.",
        subject="Snabb fråga",
        humanizer_variant="snajp:humanizer-svenska",
        scheduled_at=NU - timedelta(days=6),
    )
    await storage.mark_outreach_message_sent(
        TENANT, resultat["message"]["id"], (NU - timedelta(days=6)).isoformat()
    )
    await storage.update_send_queue_status(
        TENANT, resultat["queue_item"]["id"], status="sent", gate_checks={}
    )
    return thread["id"]


async def _svep(storage):
    with patch("app.leads.follow_up_generator.run_step", new=_stegsvar()):
        return await generate_due_follow_ups(
            storage,
            TENANT,
            now=NU,
            tenant_name="Snajp",
            context_pack="## Kontextpaket\nSnajp säljer AI-support.",
        )


@pytest.mark.anyio
async def test_forfallen_trad_far_ett_koat_granskningsutkast():
    storage = MemoryStorage()
    thread_id = await _skickad_trad(storage)
    rader = await _svep(storage)

    assert len(rader) == 1
    assert rader[0]["queued"] is True
    assert rader[0]["sekvens"] == 1
    # Autonomi default är 'draft' -> uppföljningen går till granskning.
    koade = [q for q in storage.send_queue[TENANT] if q["thread_id"] == thread_id]
    assert [q["status"] for q in koade if q["status"] == "awaiting_review"], koade

    runs = await storage.list_agent_runs(TENANT, agent_type="leads_followup")
    assert len(runs) == 1
    assert ":leads/followup-v1" in runs[0]["pack_version"]


@pytest.mark.anyio
async def test_andra_svepet_genererar_ingenting_sjalvbegransningen():
    storage = MemoryStorage()
    await _skickad_trad(storage)
    forsta = await _svep(storage)
    andra = await _svep(storage)

    assert len(forsta) == 1
    assert andra == [], "Det ogodkända utkastet ska spärra nästa varv."


@pytest.mark.anyio
async def test_svarad_trad_far_ingen_uppfoljning():
    storage = MemoryStorage()
    thread_id = await _skickad_trad(storage)
    await storage.record_inbound_reply(TENANT, thread_id=thread_id, body="Hej, интересант!")

    assert await _svep(storage) == []


@pytest.mark.anyio
async def test_grundlost_pastaende_i_uppfoljningen_koas_inte():
    from app.agent.step_runner import StepResult

    async def _pahittad_siffra(step, ledger, trace, *, task, case_context, **kwargs):
        output = {
            "sa:draft-outreach": {"subject": "Uppföljning", "body": "Våra kunder växer 300 %."},
            "snajp:humanizer-svenska": {
                "final_subject": "Uppföljning",
                "final_body": "Våra kunder växer 300 %.",
            },
        }.get(step.skill, {})
        ledger.mark_skill_injected(step.skill)
        trace.steps.append(
            StepResult(
                skill=step.skill, output=output, attempts=1, escalated=False,
                escalation_reason=None, latency_ms=1, tokens_in=1, tokens_out=1,
            )
        )
        return output

    storage = MemoryStorage()
    thread_id = await _skickad_trad(storage)
    with patch("app.leads.follow_up_generator.run_step", new=_pahittad_siffra):
        rader = await generate_due_follow_ups(
            storage, TENANT, now=NU, tenant_name="Snajp",
            context_pack="## Kontextpaket\nSnajp säljer AI-support.",
        )

    assert rader[0]["queued"] is False
    assert rader[0]["stoppad"]["grounding"], "Grindens rapport ska följa med."
    koade = [
        q for q in storage.send_queue[TENANT]
        if q["thread_id"] == thread_id and q["status"] in ("queued", "awaiting_review")
    ]
    assert koade == [], "Ingenting får ligga i kön efter en fälld grindning."
