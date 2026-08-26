"""Prospektsvarshanteringen (app/leads/svar.py) — klassificera -> agera.

Mockar bara run_step (nätverksgränsen). Lagring, kö, suppressions och
prospektstatus är riktiga kodvägar mot MemoryStorage.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.leads.svar import KLASSER, hantera_prospektsvar
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _stegsvar(svar_per_skill: dict):
    """En run_step-ersättare som svarar per skill och loggar anropen.

    Speglar den riktiga run_steps kontrakt: varje anrop appendar en StepResult
    till trace — språkgrinden läser humanizer-varianten ur trace.skills_used,
    så en fejk som inte appendar ger ett annat flöde än produktionen."""
    from app.agent.step_runner import StepResult

    anrop: list[str] = []

    async def _run_step(step, ledger, trace, *, task, case_context, **kwargs):
        anrop.append(step.skill)
        output = dict(svar_per_skill.get(step.skill) or {})
        ledger.mark_skill_injected(step.skill)
        ledger.executed_order.append(step.skill)
        trace.steps.append(
            StepResult(
                skill=step.skill,
                output=output,
                attempts=1,
                escalated=False,
                escalation_reason=None,
                latency_ms=1,
                tokens_in=10,
                tokens_out=5,
            )
        )
        return output

    return _run_step, anrop


async def _tradd_med_skickat(storage) -> str:
    """Ett prospekt med en tråd och ETT skickat mejl + EN köad uppföljning."""
    prospect = await storage.create_prospect(
        TENANT, company_name="Nordiska Verktyg AB", contact_email="vd@nordiskaverktyg.se"
    )
    thread = await storage.ensure_outreach_thread(TENANT, prospect_id=prospect["id"])
    resultat = await storage.queue_outreach_message(
        TENANT,
        thread_id=thread["id"],
        body="Hej! Första mejlet.",
        subject="Snabb fråga",
        humanizer_variant="snajp:humanizer-svenska",
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    await storage.mark_outreach_message_sent(
        TENANT, resultat["message"]["id"], datetime.now(timezone.utc) - timedelta(days=5)
    )
    await storage.update_send_queue_status(
        TENANT, resultat["queue_item"]["id"], status="sent", gate_checks={}
    )
    # En framtida uppföljning ligger i kön — den ska påverkas av svaret.
    await storage.queue_outreach_message(
        TENANT,
        thread_id=thread["id"],
        body="Uppföljning.",
        subject="Re: Snabb fråga",
        humanizer_variant="snajp:humanizer-svenska",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
    )
    return thread["id"]


async def _kor(storage, thread_id, body, svar_per_skill):
    steg, anrop = _stegsvar(svar_per_skill)
    with patch("app.leads.svar.run_step", new=steg), patch(
        "app.leads.svar.skicka_prioriterat", new=AsyncMock(return_value=True)
    ) as mejl:
        resultat = await hantera_prospektsvar(
            storage,
            TENANT,
            thread_id=thread_id,
            body=body,
            tenant_name="Snajp",
            context_pack="## Kontextpaket\nSnajp säljer AI-support till e-handlare.",
        )
    return resultat, anrop, mejl


@pytest.mark.anyio
async def test_svaret_sparas_alltid_som_inbound_rad():
    """Raden är det som gör Svar-fliken levande OCH det som stoppar
    uppföljningsgeneratorn — den skrivs före all klassificering."""
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    await _kor(storage, thread_id, "Interessant, berätta mer!", {
        "sa:call-summary": {"klass": "positivt"},
        "sa:call-prep": {"prep_notes": "Ring innan lunch."},
    })

    svar = await storage.list_replies(TENANT)
    assert len(svar) == 1
    assert svar[0]["body"] == "Interessant, berätta mer!"
    thread = await storage.get_outreach_thread(TENANT, thread_id)
    assert thread["last_inbound_at"] is not None


@pytest.mark.anyio
async def test_positivt_svar_ger_handoff_avbruten_ko_och_notis():
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    resultat, anrop, mejl = await _kor(storage, thread_id, "Ja, boka gärna ett möte.", {
        "sa:call-summary": {"klass": "positivt"},
        "sa:call-prep": {"prep_notes": "Vill se demo. Fråga om volym.", "suggested_questions": [], "risks": []},
    })

    assert resultat["klass"] == "positivt"
    assert resultat["handoff"] is True
    assert resultat["cancelled_sends"] == 1, "Den köade uppföljningen skulle ställas in."
    assert "sa:call-prep" in anrop, "Människan som tar över ska få ett underlag."
    assert resultat["queued"] is False, "Agenten svarar inte själv på ett positivt svar."
    mejl.assert_awaited()
    prospekt = (await storage.list_prospects(TENANT))[0]
    assert prospekt["status"] == "meeting"


@pytest.mark.anyio
async def test_invandning_ger_granskningsutkast_aldrig_autosand():
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    # Autonominivån är maximal — utkastet ska ÄNDÅ till granskning.
    await storage.set_agent_settings(TENANT, agent_type="leads", settings={"autonomy": "auto_send"})
    resultat, anrop, _ = await _kor(storage, thread_id, "Vi har redan en leverantör.", {
        "sa:call-summary": {"klass": "invandning", "invandning_karna": "Har redan leverantör."},
        "mk:sales-enablement": {"subject": "Re: Snabb fråga", "body": "Förstår — många vi pratar med hade det."},
        "snajp:humanizer-svenska": {"final_subject": "Re: Snabb fråga", "final_body": "Förstår dig — de flesta vi pratar med hade redan en leverantör."},
    })

    assert resultat["klass"] == "invandning"
    assert resultat["queued"] is True
    koade = [q for q in storage.send_queue[TENANT] if q["status"] == "awaiting_review"]
    assert len(koade) == 1, "Svarsutkastet ska ligga i granskningskön, oavsett autonominivå."
    assert "snajp:humanizer-svenska" in anrop, "Humaniseraren är sista handen även på svar."


@pytest.mark.anyio
async def test_negativt_svar_staller_in_kon_och_stanger_prospektet():
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    resultat, _, _ = await _kor(storage, thread_id, "Nej tack, inte aktuellt.", {
        "sa:call-summary": {"klass": "negativt"},
    })

    assert resultat["cancelled_sends"] == 1
    assert resultat["queued"] is False
    assert resultat["suppressed"] is False, "Ett nej suppressar inte — bara en uttrycklig begäran."
    prospekt = (await storage.list_prospects(TENANT))[0]
    assert prospekt["status"] == "lost"


@pytest.mark.anyio
async def test_avregistrering_suppressar_adressen():
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    resultat, _, _ = await _kor(storage, thread_id, "Sluta mejla mig.", {
        "sa:call-summary": {"klass": "avregistrering"},
    })

    assert resultat["suppressed"] is True
    assert "vd@nordiskaverktyg.se" in await storage.list_suppressions(TENANT)
    prospekt = (await storage.list_prospects(TENANT))[0]
    assert prospekt["status"] == "suppressed"


@pytest.mark.anyio
async def test_autosvar_skjuter_kon_i_stallet_for_att_stalla_in():
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    fore = [q["scheduled_at"] for q in storage.send_queue[TENANT] if q["status"] == "queued"]
    resultat, _, _ = await _kor(storage, thread_id, "Jag är på semester till v.36.", {
        "sa:call-summary": {"klass": "autosvar"},
    })

    assert resultat["rescheduled_sends"] == 1
    efter = [q["scheduled_at"] for q in storage.send_queue[TENANT] if q["status"] == "queued"]
    assert efter != fore, "Köposten skulle ha flyttats framåt."
    assert resultat["cancelled_sends"] == 0


@pytest.mark.anyio
async def test_okand_klass_faller_till_fraga_inte_till_krasch():
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    resultat, _, _ = await _kor(storage, thread_id, "??", {
        "sa:call-summary": {"klass": "nagot_pahittat"},
        "mk:sales-enablement": {"subject": "Re:", "body": "Tack för ditt svar — vad menar du?"},
        "snajp:humanizer-svenska": {"final_subject": "Re:", "final_body": "Tack för svaret — berätta gärna vad du menar."},
    })
    assert resultat["klass"] == "fraga"


@pytest.mark.anyio
async def test_grundlost_pastaende_i_svarsutkastet_gar_till_manniska():
    """INV-GROUND-001 gäller svar: en påhittad siffra köas inte."""
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    resultat, _, mejl = await _kor(storage, thread_id, "Vad kostar det?", {
        "sa:call-summary": {"klass": "fraga", "fraga_karna": "Pris."},
        "mk:sales-enablement": {"subject": "Re:", "body": "Våra kunder sparar 40 % på supporten."},
        "snajp:humanizer-svenska": {"final_subject": "Re:", "final_body": "Våra kunder sparar 40 % på supporten."},
    })

    assert resultat["queued"] is False
    assert resultat["handoff"] is True
    assert resultat["grounding"]["ok"] is False
    mejl.assert_awaited()


@pytest.mark.anyio
async def test_hotfullt_svar_avbryts_i_kod_utan_klassificeringssteg():
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    resultat, anrop, mejl = await _kor(storage, thread_id, "jag ska döda dig", {})

    assert resultat["klass"] == "avbrutet"
    assert anrop == [], "Inget LLM-anrop på ett avbrutet samtal."
    assert resultat["cancelled_sends"] == 1
    mejl.assert_awaited()


@pytest.mark.anyio
async def test_agent_run_loggas_med_steglogg():
    storage = MemoryStorage()
    thread_id = await _tradd_med_skickat(storage)
    await _kor(storage, thread_id, "Nej tack.", {"sa:call-summary": {"klass": "negativt"}})

    runs = await storage.list_agent_runs(TENANT, agent_type="leads_svar")
    assert len(runs) == 1
    assert ":leads/reply-v1" in runs[0]["pack_version"]


def test_klasserna_ar_de_koden_agerar_pa():
    assert KLASSER == ("positivt", "invandning", "fraga", "negativt", "avregistrering", "autosvar")
