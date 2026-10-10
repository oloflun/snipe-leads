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
from ..leads.signatur import HALSNING, med_signatur, normalisera as normalisera_signatur
from ..leads.timing_gate import check_cold_outreach_gate
from ..leads.utskicksfot import avregistreringslank, bygg_fot, med_fot
from ..notifications.prioriterat_mejl import skicka_prioriterat
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
    return await lagstadgad_fot(outreach.storage, outreach.tenant_id, outreach.prospect_email, brodtext)


async def lagstadgad_fot(storage, tenant_id: str, prospect_email: str | None, brodtext: str) -> str:
    """Foten för en brödtext, eller texten oförändrad när underlaget saknas
    (se _med_lagstadgad_fot). Också Godkänn och skicka går hit
    (scheduler.skicka_godkant): ett utkast skrivet innan kundregistret var
    ifyllt får sin fot när det godkänns, i stället för att stoppas av regel 1."""
    from ..config import get_settings  # lokalt: undviker cirkulär import vid modulladdning

    bas_url = get_settings().publik_bas_url
    tenant = await storage.get_tenant(tenant_id) or {}
    foretagsnamn = str(tenant.get("company_name") or tenant.get("name") or "").strip()
    orgnr = str(tenant.get("orgnr") or "").strip()
    postadress = str(tenant.get("postal_address") or "").strip()

    # Org.nr och postadress är inte krav (Anton 2026-10-10): foten tar med dem
    # när kundregistret har dem.
    if not (bas_url and foretagsnamn and prospect_email):
        return brodtext

    token = await storage.avregistreringstoken(tenant_id, email=prospect_email)
    return med_fot(
        brodtext,
        fot=bygg_fot(
            foretagsnamn=foretagsnamn,
            orgnr=orgnr,
            postadress=postadress,
            lank=avregistreringslank(bas_url, token),
            kontakt_epost=str(tenant.get("contact_email") or "").strip(),
            # Ur kundregistret (migration 073). Saknas den byggs foten utan
            # policyrad och send_guard regel 2 blockerar med besked — samma
            # fail-closed-mönster som resten av underlaget.
            policy_url=str(tenant.get("policy_url") or "").strip(),
        ),
    )


async def _queue_outreach_draft_impl(
    outreach: OutreachContext,
    *,
    subject: str,
    body: str,
    language_state: str,
    humanizer_variant: str,
    force_review: bool = False,
    stilkontroll: bool = False,
) -> str:
    # Textkvalitetslagret (app/textkvalitet.py): sista efterkontrollen innan
    # texten kan nå en kund. Platshållare ("[förnamn]") kontrolleras på
    # RÅTEXTEN — finalize_outreach_body raderar dem annars tyst och lämnar
    # "Hej ," eller en mening med ett saknat ord, vilket är exakt de fel
    # kunder har sett. Därefter putsas den strippade texten, med
    # LLM-korrektur bara om något flaggats. Kvarstår en allvarlig
    # anmärkning tvingas utkastet till mänsklig granskning — åt det
    # försiktiga hållet, precis som force_review. Allt körs FÖRE sidfoten,
    # som är kodens egen text.
    from ..textkvalitet import kontrollera, sakra_utgaende_text

    sprak = "en" if language_state == "en_confirmed" else "sv"
    platshallare = [
        a for a in kontrollera(body, sprak=sprak).allvarliga if a.kod == "platshallare"
    ]

    finalized_body = finalize_outreach_body(body)
    kvalitet = await sakra_utgaende_text(finalized_body, sprak=sprak, alltid_korrektur=True)
    finalized_body = kvalitet.text
    granskningsskal: str | None = None
    if kvalitet.kraver_granskning or platshallare:
        force_review = True
        delar = [a.beskrivning for a in platshallare] + (
            [kvalitet.sammanfattning()] if kvalitet.kraver_granskning else []
        )
        granskningsskal = "; ".join(delar)

    # Stilkontrollen (app/leads/stilkontroll.py) för kalla första mejl: AI-
    # och robotmarkörer, och samma ingång eller uppmaning som ett annat utkast
    # som väntar på granskning (körningens andra mejl). Fäller inget, men ett
    # fynd tvingar granskning, och skälet står på köposten (`held`) så att
    # granskaren ser det.
    if stilkontroll:
        from ..leads import stilkontroll as stil

        andra = [
            str(r.get("body") or "")
            for r in await outreach.storage.list_review_queue(outreach.tenant_id)
            if r.get("thread_id") != outreach.thread_id
        ]
        stilfynd = stil.kontrollera(finalized_body).anmarkningar + stil.mot_andra(finalized_body, andra)
        if stilfynd:
            force_review = True
            granskningsskal = "; ".join(
                [*([granskningsskal] if granskningsskal else []), *(a.beskrivning for a in stilfynd)]
            )

    # Signaturen (kodens text, inte modellens) läggs på efter kvalitets-
    # kontrollen och före foten — vid köningen, så att granskningstexten är
    # utskickstexten. Se app/leads/signatur.py. Inställningarna läses här och
    # återanvänds av autonomigrinden nedan — en läsning, inte två.
    agent_settings = await outreach.storage.get_agent_settings(
        outreach.tenant_id, agent_type="leads"
    )
    signatur = normalisera_signatur(agent_settings.get("signatur"))
    if signatur:
        finalized_body = med_signatur(finalized_body, signatur, halsning=HALSNING[sprak])

    finalized_body = await _med_lagstadgad_fot(outreach, finalized_body)

    try:
        check_send_gate(language_state=language_state, humanizer_variant=humanizer_variant)
    except LanguageGateError as error:
        outreach.escalated = True
        outreach.escalation_reason = f"Språkgrinden vägrade köa utkastet: {error}"
        return json.dumps({"queued": False, "error": str(error)}, ensure_ascii=False)

    # Ett väntande utkast per tråd (2026-10-08). Kön har ingen koppling till
    # VILKET utkast en post gäller: sändaren tar trådens senaste osända. Två
    # jobb för samma lead gav två utkast, och ett godkänt utkast hade gått ut
    # med det nyare, ogranskade utkastets text. Ett godkänt utkast står kvar
    # (granskaren har sagt ja till just det); ett ogranskat ersätts.
    from ..leads.scheduler import godkannande

    vantande = await outreach.storage.list_pending_sends(outreach.tenant_id, outreach.thread_id)
    if any(p.get("status") == "queued" and godkannande(p) for p in vantande):
        return json.dumps(
            {"queued": False, "error": "Ett godkänt utkast väntar redan på att skickas i den här tråden."},
            ensure_ascii=False,
        )
    if vantande:
        await outreach.storage.cancel_pending_sends(outreach.tenant_id, outreach.thread_id)

    now = datetime.now(timezone.utc)
    timing = check_cold_outreach_gate(now)
    # Köar ändå om vi är utanför fönstret just NU — scheduled_at sätts till
    # nästa dag 08:00 lokal tid i stället för "nu". Schemaläggaren kör
    # grindarna igen ändå vid faktisk utskickstid (Del J).
    # nasta_sandtid: nästa vardag 08:00 svensk tid. Förut sattes dagens 08:00
    # UTC, en tid som redan passerat (ofarligt, grinden prövar igen, men fel).
    from ..leads.utkaststatus import nasta_sandtid

    nasta = None if timing.allowed else nasta_sandtid(now, now=now)
    scheduled_at = datetime.fromisoformat(nasta) if nasta else now

    # Kundens autonominivå avgör om utkastet får gå till schemaläggaren eller
    # måste granskas av en människa först. Regeln bor i app/leads/autonomy.py
    # och anropas från exakt två ställen — här och i scheduler.process_due_item.
    #
    # `force_review` åsidosätter autonomin ÅT DET FÖRSIKTIGA HÅLLET, aldrig
    # tvärtom: ett svar i ett levande samtal (app/leads/svar.py) granskas
    # alltid av en människa, oavsett vilken nivå kunden valt för den utgående
    # sekvensen.
    # Två skäl till granskning oavsett nivå (2026-10-07): en testkörning
    # skickar aldrig till riktiga bolag, och utan schemaläggare
    # (SEND_QUEUE_POLL_SECONDS osatt, i dag i båda miljöerna) blev ett
    # 'queued' utkast liggande osynligt — varken skickat eller granskningsbart.
    from ..config import get_settings

    if force_review or outreach.is_test or get_settings().send_queue_poll_seconds <= 0:
        queue_status = "awaiting_review"
    else:
        action = allowed_action(agent_settings.get("autonomy"), outreach.sequence_index)
        queue_status = "queued" if action == "send" else "awaiting_review"

    result = await outreach.storage.queue_outreach_message(
        outreach.tenant_id,
        thread_id=outreach.thread_id,
        body=finalized_body,
        subject=subject,
        humanizer_variant=humanizer_variant,
        scheduled_at=scheduled_at,
        status=queue_status,
        gate_checks={"held": granskningsskal} if granskningsskal else None,
    )
    outreach.queued = True
    svar = {
        "queued": True,
        "queue_item_id": result["queue_item"]["id"],
        "status": queue_status,
        "awaiting_review": queue_status == "awaiting_review",
    }
    if granskningsskal:
        svar["textkvalitet"] = granskningsskal
    return json.dumps(svar, ensure_ascii=False)


async def _request_human_handoff_impl(outreach: OutreachContext, reason: str) -> str:
    """Den faktiska överlämningspunkten i leads.

    ## Varför mejlet skickas här och inte i `app/leads/handoff.py`

    `handoff.py` bär namnet, men `route_handoff()` där har INGEN
    produktionsanropare — `app/leads/autonomy.py` säger det rakt ut på två
    ställen ("handoff.py saknar produktionsanropare", och autonominivån
    `meeting` är avstängd just därför). Att koppla mejlet dit hade gett en
    sändväg som aldrig går.

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
    await skicka_prioriterat(
        "Leads-tråd lämnad till människa",
        tenant_id=outreach.tenant_id,
        # Tråd-id, inte prospektets mejladress. Adressen är personuppgift om en
        # utomstående, och tråd-id:t pekar ut samma sak för den som ska agera —
        # samma hållning som prioriterat_mejl:s docstring beskriver för kundens
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
