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

from ..leads.autonomy import allowed_action
from ..leads.language_gate import LanguageGateError, check_send_gate
from ..leads.outreach_playbook import finalize_outreach_body
from ..leads.timing_gate import check_cold_outreach_gate
from ..leads.utskicksfot import avregistreringslank, bygg_fot, med_fot
from ..notifications.internlarm import larma
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


async def _med_lagstadgad_fot(outreach: OutreachContext, brodtext: str) -> str:
    """Lägger på avsändaridentifikation, ändamål, källa och avregistreringslänk.

    KODEN skriver den, inte modellen — se app/leads/utskicksfot.py för varför.
    Det här är den enda anropsplatsen, och den ligger vid köningen så att den
    text en människa granskar i dashboarden är exakt den text som skickas.

    SAKNAS UNDERLAGET LÄGGS INGEN FOT PÅ, och det är avsiktligt. En halv
    sidfot hade passerat regel 2 (länken finns) och fallit på regel 1 med ett
    diffust "sidfoten saknar postadress" — medan den verkliga orsaken är att
    tenanten aldrig fyllt i sina bolagsuppgifter. Utan fot fälls utskicket av
    regel 1 med hela listan över vad som saknas, vilket är det besked som går
    att åtgärda.
    """
    from ..config import get_settings  # lokalt: undviker cirkulär import vid modulladdning

    bas_url = get_settings().publik_bas_url
    tenant = await outreach.storage.get_tenant(outreach.tenant_id) or {}
    foretagsnamn = str(tenant.get("company_name") or tenant.get("name") or "").strip()
    orgnr = str(tenant.get("orgnr") or "").strip()
    postadress = str(tenant.get("postal_address") or "").strip()

    if not (bas_url and foretagsnamn and orgnr and postadress and outreach.prospect_email):
        return brodtext

    token = await outreach.storage.avregistreringstoken(
        outreach.tenant_id, email=outreach.prospect_email
    )
    return med_fot(
        brodtext,
        fot=bygg_fot(
            foretagsnamn=foretagsnamn,
            orgnr=orgnr,
            postadress=postadress,
            lank=avregistreringslank(bas_url, token),
            kontakt_epost=str(tenant.get("contact_email") or "").strip(),
        ),
    )


async def _queue_outreach_draft_impl(
    outreach: OutreachContext, *, subject: str, body: str, language_state: str, humanizer_variant: str
) -> str:
    finalized_body = finalize_outreach_body(body)
    finalized_body = await _med_lagstadgad_fot(outreach, finalized_body)

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

    # Kundens autonominivå avgör om utkastet får gå till schemaläggaren eller
    # måste granskas av en människa först. Regeln bor i app/leads/autonomy.py
    # och anropas från exakt två ställen — här och i scheduler.process_due_item.
    settings = await outreach.storage.get_agent_settings(outreach.tenant_id, agent_type="leads")
    action = allowed_action(settings.get("autonomy"), outreach.sequence_index)
    queue_status = "queued" if action == "send" else "awaiting_review"

    result = await outreach.storage.queue_outreach_message(
        outreach.tenant_id,
        thread_id=outreach.thread_id,
        body=finalized_body,
        subject=subject,
        humanizer_variant=humanizer_variant,
        scheduled_at=scheduled_at,
        status=queue_status,
    )
    outreach.queued = True
    return json.dumps(
        {
            "queued": True,
            "queue_item_id": result["queue_item"]["id"],
            "status": queue_status,
            "awaiting_review": queue_status == "awaiting_review",
        },
        ensure_ascii=False,
    )


async def _request_human_handoff_impl(outreach: OutreachContext, reason: str) -> str:
    """Den faktiska överlämningspunkten i leads.

    ## Varför larmet sitter här och inte i `app/leads/handoff.py`

    `handoff.py` bär namnet, men `route_handoff()` där har INGEN
    produktionsanropare — `app/leads/autonomy.py` säger det rakt ut på två
    ställen ("handoff.py saknar produktionsanropare", och autonominivån
    `meeting` är avstängd just därför). Att koppla larmet dit hade gett en
    larmväg som aldrig går.

    Det här är i stället choke pointen som faktiskt körs: den anropas dels av
    verktyget `request_human_handoff` (modellens väg), dels av fyra kodvägar i
    `leads_agent.run_outreach_draft` — brutet utdatakontrakt, tom brödtext,
    kvarstående ostött påstående efter reparation, och brutet kontrakt i
    reparationsstegen. Alla fyra slutar med att utkastet INTE köas och att en
    människa måste ta över.
    """
    outreach.escalated = True
    outreach.escalation_reason = reason

    # Nyckeln är TRÅDEN, inte anropet. Modellen kan anropa verktyget flera
    # gånger i samma körning, och kodvägarna i run_outreach_draft kan följa på
    # varandra (en reparationsrunda som själv bryter kontraktet). Det är en
    # överlämning, alltså ett mejl.
    await larma(
        "Leads-tråd lämnad till människa",
        tenant_id=outreach.tenant_id,
        # Tråd-id, inte prospektets mejladress. Adressen är personuppgift om en
        # utomstående, och tråd-id:t pekar ut samma sak för den som ska agera —
        # samma hållning som internlarmets docstring beskriver för kundens
        # ärendetext.
        vad=f"Utkastet i tråd {outreach.thread_id} köades inte.",
        varfor=reason,
        nyckel=f"leads-handoff:{outreach.tenant_id}:{outreach.thread_id}",
    )
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
