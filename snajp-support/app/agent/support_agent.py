"""Snajp-Support: support/v1 som EN LLM-KÖRNING PER SKILL-STEG (Del C).

Tidigare version konkatenerade alla sju cs:-skills till en systemprompt och
lät en agentloop göra allt. Det gjorde läsgarantin overifierbar: man kunde
se vad som INJICERATS, aldrig vad som faktiskt använts.

Nu: varje steg är ett eget JSON-anrop med eget utdatakontrakt
(app/agent/step_runner.py), och SIDOEFFEKTERNA görs i kod här — inte av
modellen via verktyg. Modellen resonerar, koden agerar. Det gör att
- ett ärende alltid får kund/ärende/meddelanden sparade i rätt ordning,
- eskalering aldrig är beroende av att modellen kom ihåg att anropa ett verktyg,
- hela kedjan loggas till agent_runs.step_log (G10) och kan granskas i efterhand.
"""

from __future__ import annotations

import time
from typing import Any

from ..agentcore.packs import RunLedger
from ..config import CATEGORY_LABELS, get_settings
from ..storage.base import Storage
from .retention_classifier import classify_cancellation_risk, is_cancellation_risk
from .step_runner import RunTrace, run_step
from .support_playbook import SUPPORT_V1
from .tools import strip_markdown
from .vision import describe_image

# Sentiment under denna tröskel eskalerar oavsett vad modellen tycker
# (samma regel som tidigare låg i den handskrivna prompten).
SENTIMENT_ESCALATION_THRESHOLD = 0.3


def _steps_by_skill() -> dict[str, Any]:
    return {step.skill: step for step in SUPPORT_V1.steps}


async def run_support_agent(
    storage: Storage,
    tenant_id: str,
    *,
    message: str,
    subject: str,
    channel: str,
    customer_email: str | None,
    customer_name: str | None,
    attachments: list[str],
) -> dict[str, Any]:
    started = time.monotonic()
    settings = get_settings()
    config = await storage.get_channel_config(tenant_id, channel)
    taxonomy = await storage.get_agent_taxonomy(tenant_id)
    steps = _steps_by_skill()

    # G9: bilder beskrivs av vision-sidovagnen och kastas — aldrig lagrade.
    vision_note = ""
    if attachments:
        descriptions = [await describe_image(url) for url in attachments]
        vision_note = "\n\n[Bildbeskrivning]:\n" + "\n".join(descriptions)

    # Del E steg 6: klassificeraren körs i KOD före playbooken.
    try:
        intent, dissatisfaction = await classify_cancellation_risk(message)
    except Exception:  # noqa: BLE001 — en trasig klassificerare får inte fälla ärendet
        intent, dissatisfaction = 0.0, 0.0
    cancellation_risk = is_cancellation_risk(intent, dissatisfaction)

    case_context = (
        f"## Ärendet\nKanal: {channel} (ton: {config['tone']}, max {config['max_length']} tecken)\n"
        f"Kund: {customer_name or 'okänd'} <{customer_email or 'okänd'}>\n"
        f"Ämne: {subject or '(inget)'}\n\n"
        f"Kundens meddelande:\n{message}{vision_note}\n\n"
        f"Giltiga kategorier för den här kunden: {', '.join(taxonomy)}"
    )

    ledger = RunLedger(satisfied={"context_pack"})
    trace = RunTrace()

    # --- Steg 1: triage ----------------------------------------------------
    triage = await run_step(
        steps["cs:ticket-triage"],
        ledger,
        trace,
        task=(
            "Klassificera ärendet. Returnera JSON med: category (exakt ett av de "
            "giltiga), priority (P1-P4), sentiment (0.0-1.0), escalate (bool), "
            "reasoning (svenska)."
        ),
        case_context=case_context,
    )
    category = triage.get("category") if triage.get("category") in taxonomy else "ovrigt"
    sentiment = max(0.0, min(1.0, float(triage.get("sentiment") or 0.5)))

    # --- Kod: kund, ärende, inkommande meddelande --------------------------
    customer = await storage.find_or_create_customer(
        tenant_id, email=customer_email, phone=None, name=customer_name
    )
    history = await storage.get_customer_history(tenant_id, customer["id"])
    ticket = await storage.create_ticket(
        tenant_id,
        customer_id=customer["id"],
        subject=subject or message[:80],
        category=category,
        channel=channel,
        priority="high" if triage.get("priority") in ("P1", "P2") else "normal",
    )
    await storage.save_message(
        tenant_id,
        conversation_id=ticket["conversation_id"],
        direction="inbound",
        content=message,
        sentiment=sentiment,
        has_image=bool(attachments),
    )

    # --- Kod: KB-sökning (underlaget cs:customer-research resonerar kring) --
    embedding = None
    try:
        from .embeddings import embed_text

        embedding = await embed_text(f"{subject} {message}".strip())
    except Exception:  # noqa: BLE001 — utan embeddings används fulltext-fallback
        embedding = None
    articles = await storage.search_kb(tenant_id, f"{subject} {message}".strip(), embedding=embedding)
    kb_block = "\n\n".join(f"### {a['title']}\n{a['content']}" for a in articles) or "(inga träffar)"

    # --- Steg 2: research --------------------------------------------------
    research = await run_step(
        steps["cs:customer-research"],
        ledger,
        trace,
        task=(
            "Bedöm vad kunskapsbasen faktiskt svarar på och med vilken konfidens. "
            "Returnera JSON: findings (svenska), confidence (0.0-1.0), "
            "kb_supports_answer (bool), missing_info (svenska eller null)."
        ),
        case_context=(
            f"{case_context}\n\n## Kunskapsbas (ENDA tillåtna faktakällan)\n{kb_block}\n\n"
            f"Tidigare kontakter från kunden: {len(history)}"
        ),
    )

    # --- Steg 3: utkast ----------------------------------------------------
    draft = await run_step(
        steps["cs:draft-response"],
        ledger,
        trace,
        task=(
            "Skriv ett svar till kunden, grundat ENBART i kunskapsbasen ovan. "
            "Ren text, ingen markdown. Returnera JSON: draft (svenska)."
        ),
        case_context=f"{case_context}\n\n## Kunskapsbas\n{kb_block}\n\n## Research\n{research.get('findings', '')}",
    )

    # --- Steg 4: eskaleringsbedömning --------------------------------------
    escalation = await run_step(
        steps["cs:customer-escalation"],
        ledger,
        trace,
        task=(
            "Avgör om ärendet måste till en människa. Eskalera ALLTID vid: "
            "återbetalning/kompensation, juridik/ARN/Konsumentverket, GDPR-radering, "
            "eller om kunskapsbasen saknar svar. Returnera JSON: "
            "should_escalate (bool), reason (svenska eller null)."
        ),
        case_context=(
            f"{case_context}\n\n## Research\n{research.get('findings', '')}\n"
            f"kb_supports_answer: {research.get('kb_supports_answer')}"
        ),
    )

    # Eskalering avgörs i KOD av tre oberoende villkor — inte av modellen ensam.
    escalated = bool(
        escalation.get("should_escalate")
        or triage.get("escalate")
        or sentiment < SENTIMENT_ESCALATION_THRESHOLD
        or not articles
        or cancellation_risk
    )
    escalation_reason = escalation.get("reason") or (
        "retention_risk" if cancellation_risk else None
    )
    if escalated and not escalation_reason:
        escalation_reason = (
            "Ingen träff i kunskapsbasen" if not articles else "Lågt sentiment eller triageflagga"
        )

    # --- Steg 5: KB-artikel (fångar ny kunskap tillbaka) -------------------
    await run_step(
        steps["cs:kb-article"],
        ledger,
        trace,
        task=(
            "Bedöm om det här ärendet avslöjar en kunskapslucka värd en KB-artikel. "
            "Returnera JSON: should_create (bool), title (svenska eller null), "
            "content (svenska eller null)."
        ),
        case_context=f"{case_context}\n\n## Kunskapsbas\n{kb_block}",
    )

    # --- Steg 6: retention (villkorat) -------------------------------------
    current_draft = draft.get("draft", "")
    if cancellation_risk:
        retention_playbook = await storage.get_latest_context_doc(
            tenant_id, kind="retention_playbook"
        )
        playbook_text = (
            retention_playbook["content"]
            if retention_playbook
            else "(INGEN retentionsplaybook finns för den här kunden — du får därför "
            "INTE erbjuda något alls. Bekräfta, fastställ, och lämna över till människa.)"
        )
        retention = await run_step(
            steps["snajp:retention-conversation"],
            ledger,
            trace,
            task=(
                "Kunden signalerar uppsägning/missnöje. Skriv om utkastet enligt "
                "skillens fyra hårda regler. Erbjud ALDRIG något som inte ordagrant "
                "står i retentionsplaybooken nedan. Returnera JSON: revised_draft "
                "(svenska), offers_made (lista, tom om inga)."
            ),
            case_context=(
                f"{case_context}\n\n## Kundens retentionsplaybook\n{playbook_text}\n\n"
                f"## Nuvarande utkast\n{current_draft}"
            ),
        )
        current_draft = retention.get("revised_draft") or current_draft

    # --- Steg 7: humanizer (ALLTID sist) -----------------------------------
    humanized = await run_step(
        steps["snajp:humanizer-svenska"],
        ledger,
        trace,
        task=(
            "Gör texten naturlig svenska enligt skillen. Behåll all sakinformation. "
            "Ren text, ingen markdown. Returnera JSON: final_reply (svenska)."
        ),
        case_context=f"{case_context}\n\n## Text att humanisera\n{current_draft}",
    )

    reply = strip_markdown(humanized.get("final_reply") or current_draft or "").strip()
    if not reply:
        reply = (
            "Tack för ditt meddelande! Jag har öppnat ett ärende och en kollega "
            "återkommer så snart som möjligt."
        )
    if len(reply) > config["max_length"]:
        reply = reply[: config["max_length"] - 1].rstrip() + "…"

    # --- Kod: sidoeffekter -------------------------------------------------
    if escalated:
        await storage.update_ticket(
            tenant_id,
            ticket["id"],
            status="escalated",
            priority="high",
            escalation_reason=escalation_reason,
        )
    await storage.save_message(
        tenant_id,
        conversation_id=ticket["conversation_id"],
        direction="outbound",
        content=reply,
        sentiment=None,
        has_image=False,
    )
    await storage.log_metric(
        tenant_id, ticket_id=ticket["id"], metric_name="sentiment", value=sentiment
    )

    latency_ms = int((time.monotonic() - started) * 1000)
    manifest_hash = _manifest_hash()
    await storage.log_agent_run(
        tenant_id,
        agent_type="support",
        pack_version=f"{manifest_hash}:{SUPPORT_V1.name}",
        skills_used=trace.skills_used,
        input_text=message,
        output_text=reply,
        step_log=trace.as_log(),
        tokens_in=trace.total_tokens_in,
        tokens_out=trace.total_tokens_out,
        latency_ms=latency_ms,
    )

    return {
        "reply": reply,
        "ticket_id": ticket["id"],
        "customer_id": customer["id"],
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Övrigt"),
        "sentiment": sentiment,
        "escalated": escalated,
        "escalation_reason": escalation_reason,
        "kb_sources": [{"title": a["title"], "similarity": a["similarity"]} for a in articles],
        "returning_customer": len(history) > 0,
        "simulation": False,
        "skills_used": trace.skills_used,
        "step_log": trace.as_log(),
        "cancellation_risk": cancellation_risk,
        "pack_version": f"{manifest_hash}:{SUPPORT_V1.name}",
    }


def _manifest_hash() -> str:
    """Baseline-versionen (Del B/D) — manifestets hash över alla vendorade filer."""
    import json
    from pathlib import Path

    manifest = Path(__file__).resolve().parents[3] / "agent-core" / "manifest.json"
    if not manifest.is_file():
        return "unknown"
    return json.loads(manifest.read_text(encoding="utf-8")).get("manifest_hash", "unknown")[:12]
