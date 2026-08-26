"""Uppföljningsgeneratorn — kedjan som var designad men aldrig inkopplad.

## Vad som inte fanns förrän 2026-08-26

`follow_up.py` har sedan Del H burit HELA uppföljningslogiken — spakordning,
breakup-mejl, sekvensnummer — och anropades enbart från tester (snipe-3dx).
Skickades ett första mejl hände sedan ingenting: ingen kodväg tittade på
tysta trådar, och "uppföljningar" fanns som datastruktur men inte som
beteende.

## Formen

Två halvor, medvetet isärhållna:

  * `trad_som_ar_forfallna` — REN policy, testbar utan databas och utan
    modell: vilka trådar är förfallna, givet aggregat som lagringen räknat.
  * `generate_due_follow_ups` — I/O och LLM: skriver utkast för de förfallna
    och köar dem genom SAMMA väg som första mejlet (`_queue_outreach_draft_impl`
    -> finalize, lagstadgad fot, språkgrind, autonomi). Autonominivån avgör
    status: `draft`/`first_contact` ger awaiting_review — en uppföljning går
    ALDRIG ut utan människa på de nivåerna (allowed_action, sequence > 0).

## Spakordningen (ponytail: fast ordning, se nedan)

Del H:s modell är "svagast spak först", ur mk:offers värdeekvation. Poängen
per spak persisteras dock ingenstans i dag (offers-tabellen är oanvänd av
kodvägarna), så v1 följer LEVERS kanoniska ordning och avslutar med breakup.
# ponytail: fast spakordning; byt till build_follow_up_sequence(offers.
# value_equation_scores) när offers-raderna faktiskt skrivs av researchflödet.

## Självbegränsningen

En genererad uppföljning ligger som osänt utkast/köpost i tråden, och
`has_pending_item` gör då tråden icke-förfallen — generatorn kan inte spamma
samma tråd hur ofta den än körs. Ett inkommet svar sätter `last_inbound_at`
(app/leads/svar.py) och tar tråden ur svepet permanent: svarade trådar ägs
av svarshanteringen, inte av sekvensen.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from ..agent.leads_context import OutreachContext
from ..agent.leads_tools import _queue_outreach_draft_impl
from ..agent.step_runner import RunTrace, run_step
from ..agent.tools import strip_markdown
from ..agentcore.instruktioner import las_instruktioner
from ..agentcore.overlays import pack_version
from ..agentcore.packs import Playbook, PlaybookStep, RunLedger
from .follow_up import LEVERS
from .gissnings_gate import check_gissningar
from .grounding_gate import build_permitted_facts, check_grounding
from .language_gate import last_humanizer_variant
from .research_playbook import THINKING

logger = logging.getLogger("snajp-support.follow-up-generator")

_ROLL = "en svensk playbook för en lågmäld uppföljning i en pågående mejltråd"

#: Dagar sedan senast SKICKADE mejl innan nästa steg är förfallet, per
#: sekvensnummer (1 = första uppföljningen). Stigande avstånd: varje tyst
#: varv är ett svagare köpsignal, och tätare tryck läser som desperation.
FOLLOW_UP_DELAYS: dict[int, timedelta] = {
    1: timedelta(days=4),
    2: timedelta(days=6),
    3: timedelta(days=8),
    4: timedelta(days=10),
}

#: Max antal utgående per tråd: initialt + tre spak-uppföljningar + breakup.
MAX_OUTBOUND = len(LEVERS) + 1

#: Vinkeln per sekvensnummer. Texten går in i stegets task — modellen får
#: veta VAD uppföljningen ska trycka på, koden bestämmer VILKEN.
_VINKLAR: dict[int, str] = {
    1: (
        "Vinkel (dream_outcome): påminn kort om det utlovade utfallet — vad "
        "vardagen ser ut som när problemet är löst. Inget nytt erbjudande."
    ),
    2: (
        "Vinkel (perceived_likelihood): sänk tvivlet på att det fungerar — "
        "ett konkret, verifierbart skäl att tro på leveransen. Inga påhittade "
        "referenser eller siffror."
    ),
    3: (
        "Vinkel (time_delay): hur snabbt värdet kommer — vad som händer första "
        "veckan. Inga datumlöften som inte står i underlaget."
    ),
    4: (
        "Detta är ett BREAKUP-MEJL: sista kontakten. Kort, vänligt, inga "
        "förebråelser. Säg att du slutar höra av dig, lämna dörren öppen med "
        "ett enkelt sätt att återuppta kontakten."
    ),
}

FOLLOWUP_V1 = Playbook(
    name="leads/followup-v1",
    steps=(
        PlaybookStep(
            skill="sa:draft-outreach",
            requires=("context_pack",),
            # Komposition: hårdreglerna + uppföljningsformens egna (kort,
            # ingen förebråelse, tillför det NYA, breakup-reglerna).
            overlay=("leads-hard-rules", "leads-followup"),
            thinking=THINKING,
            temperature=0.5,
        ),
        PlaybookStep(
            skill="snajp:humanizer-svenska",
            requires=("skill:sa:draft-outreach",),
            overlay=("leads-hard-rules", "leads-followup"),
            thinking=THINKING,
            temperature=0.7,
        ),
    ),
)


def trad_som_ar_forfallna(
    threads: list[dict[str, Any]], *, now: datetime
) -> list[tuple[dict[str, Any], int]]:
    """Vilka trådar som är förfallna för nästa steg, och vilket steget är.

    Ren funktion över aggregaten från `storage.list_outreach_threads` —
    policyn ska gå att falsifiera i ett test utan databas.
    """
    forfallna: list[tuple[dict[str, Any], int]] = []
    for thread in threads:
        sent = int(thread.get("outbound_sent_count") or 0)
        if sent < 1 or sent >= MAX_OUTBOUND:
            continue  # inget initialt skickat än, eller sekvensen färdig
        if thread.get("last_inbound_at"):
            continue  # svarade trådar ägs av svarshanteringen
        if thread.get("has_pending_item"):
            continue  # nästa steg finns redan (utkast eller köpost)
        senast = thread.get("last_outbound_sent_at")
        if not senast:
            continue
        if isinstance(senast, str):
            senast = datetime.fromisoformat(senast)
        if senast.tzinfo is None:
            senast = senast.replace(tzinfo=now.tzinfo)
        if now - senast >= FOLLOW_UP_DELAYS[sent]:
            forfallna.append((thread, sent))
    return forfallna


async def generate_due_follow_ups(
    storage,
    tenant_id: str,
    *,
    now: datetime,
    tenant_name: str,
    context_pack: str,
) -> list[dict[str, Any]]:
    """Skriver och köar uppföljningsutkast för tenantens förfallna trådar.

    Returnerar en rad per behandlad tråd. Ett trasigt utkast fäller inte de
    andra trådarna — samma princip som batchkörningen.
    """
    threads = await storage.list_outreach_threads(tenant_id)
    forfallna = trad_som_ar_forfallna(threads, now=now)
    if not forfallna:
        return []

    lager = await las_instruktioner(storage, tenant_id, agent_type="leads", tenant_namn=tenant_name)
    resultat: list[dict[str, Any]] = []
    for thread, sekvens in forfallna:
        try:
            resultat.append(
                await _en_uppfoljning(
                    storage,
                    tenant_id,
                    thread=thread,
                    sekvens=sekvens,
                    tenant_name=tenant_name,
                    context_pack=context_pack,
                    lager=lager,
                )
            )
        except Exception as error:  # noqa: BLE001 — en tråd fäller inte svepet
            logger.exception("Uppföljning för tråd %s misslyckades.", thread.get("id"))
            resultat.append({"thread_id": thread.get("id"), "queued": False, "fel": str(error)})
    return resultat


async def _en_uppfoljning(
    storage,
    tenant_id: str,
    *,
    thread: dict[str, Any],
    sekvens: int,
    tenant_name: str,
    context_pack: str,
    lager,
) -> dict[str, Any]:
    started = time.monotonic()
    thread_id = str(thread["id"])
    company_name = thread.get("company_name") or "prospektet"
    prospect_email = thread.get("prospect_email") or thread.get("contact_email") or ""

    meddelanden = await storage.list_outreach_messages(tenant_id, thread_id)
    historik = "\n\n".join(
        f"{'Prospektet' if m['direction'] == 'inbound' else 'Vi'}: {(m.get('body') or '').strip()}"
        for m in meddelanden[-4:]
        if (m.get("body") or "").strip()
    )

    base = (
        f"## Uppdrag\nDu skriver uppföljning nr {sekvens} till {company_name} åt {tenant_name}. "
        f"Prospektet har inte svarat på tidigare mejl.\n\n"
        f"{context_pack}\n\n"
        f"## Tidigare mejl i tråden (skriv INTE om dem, upprepa inte innehållet)\n{historik}\n\n"
        f"## {_VINKLAR[sekvens]}"
    )

    ledger = RunLedger(satisfied={"context_pack"})
    trace = RunTrace()
    steps = FOLLOWUP_V1.steps

    draft = await run_step(
        steps[0],
        ledger,
        trace,
        task=(
            "Skriv uppföljningsmejlet enligt vinkeln ovan. KORT — 3-5 meningar. "
            "Referera naturligt till att du hört av dig förut, utan att låta "
            "förebrående. Påstå ingenting som inte står i underlaget. "
            "Returnera JSON: subject (svenska, ren text), body (svenska, ren text)."
        ),
        case_context=base,
        playbook_role=_ROLL,
        instruktioner=lager,
    )
    humaniserat = await run_step(
        steps[1],
        ledger,
        trace,
        task=(
            "Gör texten till naturlig svenska enligt skillen. Behåll all "
            "sakinformation, lägg inte till nya påståenden. Returnera JSON: "
            "final_subject (svenska), final_body (svenska, ren text)."
        ),
        case_context=(
            f"{base}\n\n## Text att humanisera\n"
            f"Ämne: {draft.get('subject', '')}\n\n{draft.get('body', '')}"
        ),
        playbook_role=_ROLL,
        instruktioner=lager,
    )
    subject = strip_markdown(humaniserat.get("final_subject") or draft.get("subject") or "").strip()
    body = strip_markdown(humaniserat.get("final_body") or draft.get("body") or "").strip()

    utfall: dict[str, Any] = {
        "thread_id": thread_id,
        "sekvens": sekvens,
        "queued": False,
        "subject": subject,
    }

    # INV-GROUND-001 gäller uppföljningar precis som första mejlet.
    facts = build_permitted_facts(
        context_pack=context_pack,
        research_evidence=(),
        offer_summary="",
        brief="",
        tenant_name=tenant_name,
        company_name=company_name,
    )
    verdict = check_grounding(f"{subject}\n\n{body}", facts)
    gissningar = check_gissningar(f"{subject}\n\n{body}")
    eskalerade = [s.skill for s in trace.steps if s.escalated]

    if not body or not verdict.ok or gissningar or eskalerade:
        utfall["stoppad"] = {
            "tom": not body,
            "grounding": verdict.as_report(),
            "gissningar": list(gissningar),
            "eskalerade_steg": eskalerade,
        }
    else:
        import json as _json

        # sequence_index avgör autonomifrågan: uppföljningar (index > 0)
        # kräver `meeting`-nivå för att gå utan granskning (allowed_action).
        context = OutreachContext(
            storage=storage,
            tenant_id=tenant_id,
            thread_id=thread_id,
            prospect_email=prospect_email,
            sequence_index=int(thread.get("outbound_sent_count") or sekvens),
        )
        svar = _json.loads(
            await _queue_outreach_draft_impl(
                context,
                subject=subject or f"Uppföljning — {company_name}",
                body=body,
                language_state=str(thread.get("language_state") or "sv"),
                humanizer_variant=last_humanizer_variant(trace.skills_used),
            )
        )
        utfall["queued"] = bool(svar.get("queued"))
        utfall["status"] = "awaiting_review" if svar.get("awaiting_review") else "queued"
        utfall["queue_item_id"] = svar.get("queue_item_id")

    await storage.log_agent_run(
        tenant_id,
        agent_type="leads_followup",
        pack_version=pack_version(FOLLOWUP_V1.name, lager.hash),
        skills_used=trace.skills_used,
        input_text=f"uppföljning {sekvens} till {company_name}",
        output_text=f"{subject}\n\n{body}",
        step_log=trace.as_log(),
        tokens_in=trace.total_tokens_in,
        tokens_out=trace.total_tokens_out,
        latency_ms=int((time.monotonic() - started) * 1000),
    )
    return utfall
