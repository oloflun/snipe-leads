"""Verktyg för leads-agenterna (onboarding, outreach). Samma princip som
app/agent/tools.py: tenant kommer ALDRIG från ett verktygsargument (INV-
SEC-002) — den läses ur kontexten, satt av servern.

INV-SEC-004: inget verktyg här kan skicka. queue_outreach_draft skriver
ENDAST till send_queue med status='queued' — app/leads/scheduler.py är den
enda kodvägen som någonsin sätter status='sent'.

Varje verktyg är en tunn @function_tool-wrapper runt en vanlig, testbar
async-funktion (_impl-suffix) — SDK:ns ToolContext är omständlig att
konstruera direkt i ett test, så testerna anropar _impl-funktionerna med
en vanlig Context-instans i stället för att gå via verktygsprotokollet.
"""

import json
from datetime import datetime, timezone

from agents import RunContextWrapper, function_tool

from ..leads.language_gate import LanguageGateError, check_send_gate
from ..leads.outreach_playbook import finalize_outreach_body
from ..leads.timing_gate import check_cold_outreach_gate
from .leads_context import OnboardingContext, OutreachContext


async def _save_context_doc_impl(onboarding: OnboardingContext, kind: str, content: str) -> str:
    if kind not in ("product_marketing", "customer_research", "retention_playbook"):
        return json.dumps({"error": f"Okänd kind: {kind}"})
    doc = await onboarding.storage.save_context_doc(
        onboarding.tenant_id, kind=kind, content=content, source="onboarding-agent"
    )
    onboarding.saved_docs.append(doc)
    if kind == "product_marketing":
        from ..leads.context_pack import materialize_product_marketing

        materialize_product_marketing(onboarding.tenant_id, content)
    return json.dumps({"saved": True, "kind": kind, "version": doc["version"]}, ensure_ascii=False)


async def _mark_onboarding_done_impl(onboarding: OnboardingContext) -> str:
    onboarding.done = True
    return json.dumps({"done": True})


async def _queue_outreach_draft_impl(
    outreach: OutreachContext, *, subject: str, body: str, language_state: str, humanizer_variant: str
) -> str:
    finalized_body = finalize_outreach_body(body)

    try:
        check_send_gate(language_state=language_state, humanizer_variant=humanizer_variant)
    except LanguageGateError as error:
        outreach.escalated = True
        outreach.escalation_reason = f"Språkgrinden vägrade köa utkastet: {error}"
        return json.dumps({"queued": False, "error": str(error)}, ensure_ascii=False)

    now = datetime.now(timezone.utc)
    timing = check_cold_outreach_gate(now)
    # Köar ändå om vi är utanför fönstret just NU — scheduled_at sätts till
    # nästa dag 08:00 lokal tid i stället för "nu". Schemaläggaren kör
    # grindarna igen ändå vid faktisk utskickstid (Del J).
    scheduled_at = now if timing.allowed else now.replace(hour=8, minute=0, second=0, microsecond=0)

    result = await outreach.storage.queue_outreach_message(
        outreach.tenant_id,
        thread_id=outreach.thread_id,
        body=finalized_body,
        subject=subject,
        humanizer_variant=humanizer_variant,
        scheduled_at=scheduled_at,
    )
    outreach.queued = True
    return json.dumps(
        {"queued": True, "queue_item_id": result["queue_item"]["id"]}, ensure_ascii=False
    )


async def _request_human_handoff_impl(outreach: OutreachContext, reason: str) -> str:
    outreach.escalated = True
    outreach.escalation_reason = reason
    return json.dumps({"escalated": True, "reason": reason}, ensure_ascii=False)


@function_tool
async def save_context_doc(
    ctx: RunContextWrapper[OnboardingContext], kind: str, content: str
) -> str:
    """Sparar ett kontextdokument från onboarding-samtalet.

    Args:
        kind: Ett av product_marketing, customer_research, retention_playbook.
        content: Det insamlade innehållet, på svenska.
    """
    return await _save_context_doc_impl(ctx.context, kind, content)


@function_tool
async def mark_onboarding_done(ctx: RunContextWrapper[OnboardingContext]) -> str:
    """Markerar onboarding som klar (alla tre kontextdokument insamlade)."""
    return await _mark_onboarding_done_impl(ctx.context)


@function_tool
async def queue_outreach_draft(
    ctx: RunContextWrapper[OutreachContext],
    subject: str,
    body: str,
    language_state: str,
    humanizer_variant: str,
) -> str:
    """Köar ett färdigt utkast för utskick. Skickar INGENTING direkt — bara
    lägger det i send_queue, som schemaläggaren senare kontrollerar
    grindarna mot igen (Del J).

    Args:
        subject: Ämnesraden, ren text.
        body: Brödtexten, plain text — ingen markdown.
        language_state: 'sv' eller 'en_confirmed', enligt trådens faktiska tillstånd.
        humanizer_variant: Vilken humanizer-skill som kördes sist (snajp:humanizer-svenska
            eller snajp:humanizer).
    """
    return await _queue_outreach_draft_impl(
        ctx.context,
        subject=subject,
        body=body,
        language_state=language_state,
        humanizer_variant=humanizer_variant,
    )


@function_tool
async def request_human_handoff(ctx: RunContextWrapper[OutreachContext], reason: str) -> str:
    """Flaggar tråden för mänsklig handoff. Agenten bokar aldrig själv och
    förhandlar aldrig pris (Fas E) — det här är det enda den kan göra när
    prospektet svarar positivt eller ställer en fråga agenten inte får
    besvara själv.

    Args:
        reason: Svensk motivering.
    """
    return await _request_human_handoff_impl(ctx.context, reason)


ONBOARDING_TOOLS = [save_context_doc, mark_onboarding_done]
OUTREACH_TOOLS = [queue_outreach_draft, request_human_handoff]
