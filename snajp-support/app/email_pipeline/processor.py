"""Processorn: triage → klassificering → ärende → utkast/autosvar/eskalering.

Säkerhetsordning (hårdast först):
1. Triagen säger eskalera (pengar/juridik/GDPR/argt) → alltid människa.
2. Ingen KB-träff → grundningsregeln tvingar eskalering.
3. Fackets regel är 'escalate' → människa.
4. Fackets regel är 'auto' OCH konfidens ≥ tröskeln OCH sentiment ej negativt
   → autosvar (skickas/simuleras + loggas).
5. Annars → utkast som väntar på mänskligt godkännande (default).

Varje steg loggas i ss_decision_log med motivering.
"""

import logging
from typing import Any

from ..config import CATEGORY_LABELS, get_settings
from ..simulation.sim_triage import classify
from ..storage.base import Storage

logger = logging.getLogger("snajp-support.processor")

_GREETING = "Hej{name}!\n\n"
_SIGNATURE = "\n\nVänliga hälsningar,\nSnajp-Support"

_ESCALATION_BODY = (
    "Tack för ditt meddelande. Jag förstår att det här är viktigt, och den här typen "
    "av ärende hanteras alltid av en av våra medarbetare. Ärendet har fått hög "
    "prioritet och all information är vidarebefordrad — du får svar från vår "
    "kundtjänst så snart som möjligt, senast inom en vardag."
)

_NO_MATCH_BODY = (
    "Tack för att du hör av dig. Jag hittar inget säkert svar på din fråga i vår "
    "kunskapsbas och gissar aldrig — därför tar en kollega över ärendet och "
    "återkommer till dig så snart som möjligt."
)

_VISION_NOTES = {
    "teknisk_support": "Jag har tittat på din bifogade skärmdump och tagit med felet i bedömningen. ",
    "retur_reklamation": "Jag har tittat på din bifogade bild av varan/förpackningen. ",
    "default": "Jag har tittat på din bifogade bild och tagit med den i bedömningen. ",
}


def _first_name(name: str | None) -> str:
    return " " + name.strip().split()[0] if name else ""


def _sim_confidence(category: str, articles: list[dict[str, Any]]) -> float:
    if category == "ovrigt":
        return 0.4
    return 0.9 if articles else 0.55


async def _triage_email(
    storage: Storage,
    tenant_id: str,
    email: dict[str, Any],
    image_urls: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Returnerar (triage-resultat med confidence/reasoning/draft_body, KB-träffar)."""
    settings = get_settings()
    query = f"{email['subject']} {email['body_text']}".strip()

    if settings.is_simulation():
        triage = classify(email["subject"], email["body_text"])
        articles = await storage.search_kb(tenant_id, query)
        triage["confidence"] = _sim_confidence(triage["category"], articles)
        triage["reasoning"] = (
            f"Nyckelordsmatchning gav facket {CATEGORY_LABELS[triage['category']]} "
            f"(sentiment {triage['sentiment']} via tonhetsheuristik, "
            f"{len(articles)} träffar i kunskapsbasen"
            + (", bild bifogad" if image_urls else "")
            + "). Simuleringsläge — deterministisk regelpipeline."
        )
        vision_note = ""
        if image_urls:
            vision_note = _VISION_NOTES.get(triage["category"], _VISION_NOTES["default"])
        if articles and not triage["escalate"]:
            triage["draft_body"] = (
                f"Tack för att du hör av dig om {CATEGORY_LABELS[triage['category']].lower()}. "
                f"{vision_note}Så här fungerar det hos oss:\n\n{articles[0]['content']}\n\n"
                "Hör gärna av dig om något är oklart!"
            )
        else:
            triage["draft_body"] = None
        triage["model"] = "simulation"
        return triage, articles

    # Riktigt läge: embeddings + gpt-4o-mini med vision (bilderna skickas med).
    from ..agent.embeddings import embed_text
    from ..agent.triage import triage_email_llm

    embedding = await embed_text(query)
    articles = await storage.search_kb(tenant_id, query, embedding=embedding)
    result = await triage_email_llm(
        sender=email["from_email"],
        subject=email["subject"],
        body=email["body_text"],
        kb_articles=articles,
        image_urls=image_urls,
    )
    result["draft_body"] = result.pop("draft_reply", None)
    result.setdefault("reasoning", "LLM-klassificering.")
    result["model"] = get_settings().model
    return result, articles


async def process_email(
    storage: Storage, tenant_id: str, email: dict[str, Any]
) -> dict[str, Any]:
    """Kör hela flödet för ett sparat mail. Kastar aldrig — fel ger status failed."""
    settings = get_settings()
    email_id = email["id"]
    try:
        await storage.update_email(tenant_id, email_id, status="processing")

        detail = await storage.get_email(tenant_id, email_id)
        image_urls = [
            a["data_url"] for a in detail.get("attachments", [])
            if a["is_image"] and a.get("data_url")
        ][:3]

        triage, articles = await _triage_email(storage, tenant_id, email, image_urls)
        kb_sources = [
            {"title": a["title"], "similarity": a["similarity"]} for a in articles
        ]

        await storage.save_classification(
            tenant_id,
            email_id=email_id,
            category=triage["category"],
            priority=triage.get("priority", "normal"),
            sentiment=triage.get("sentiment"),
            confidence=round(float(triage.get("confidence", 0.5)), 2),
            escalate=bool(triage.get("escalate")),
            escalation_reason=triage.get("escalation_reason"),
            reasoning=triage.get("reasoning", ""),
            kb_sources=kb_sources,
            model=triage.get("model", "simulation"),
        )
        await storage.log_decision(
            tenant_id,
            email_id=email_id,
            event="classified",
            detail={
                "category": triage["category"],
                "confidence": triage.get("confidence"),
                "sentiment": triage.get("sentiment"),
                "reasoning": triage.get("reasoning", ""),
            },
        )

        # CRM: kund + ärende + konversation, precis som chatt-flödet.
        customer = await storage.find_or_create_customer(
            tenant_id, email=email["from_email"], phone=None, name=email["from_name"]
        )
        ticket = await storage.create_ticket(
            tenant_id,
            customer_id=customer["id"],
            subject=email["subject"] or email["body_text"][:80],
            category=triage["category"],
            channel="email",
            priority=triage.get("priority", "normal"),
        )
        await storage.save_message(
            tenant_id,
            conversation_id=ticket["conversation_id"],
            direction="inbound",
            content=email["body_text"],
            sentiment=triage.get("sentiment"),
            has_image=bool(image_urls),
        )
        await storage.update_email(tenant_id, email_id, ticket_id=ticket["id"])

        greeting = _GREETING.format(name=_first_name(email["from_name"]))
        rules = await storage.get_category_rules(tenant_id)
        rule = rules.get(triage["category"], "draft")
        confidence = float(triage.get("confidence", 0.5))
        sentiment = triage.get("sentiment")

        # 1–2: obligatorisk eskalering (triage eller tom KB).
        must_escalate = bool(triage.get("escalate"))
        escalation_reason = triage.get("escalation_reason")
        if not must_escalate and not articles:
            must_escalate = True
            escalation_reason = "Ingen träff i kunskapsbasen — grundningsregeln kräver människa."

        if must_escalate or rule == "escalate":
            reason = escalation_reason or f"Regeln för facket {CATEGORY_LABELS[triage['category']]} kräver mänsklig granskning."
            body = _ESCALATION_BODY if must_escalate and articles else (
                _NO_MATCH_BODY if not articles else _ESCALATION_BODY
            )
            content = (greeting + body + _SIGNATURE).strip()
            await storage.update_ticket(
                tenant_id, ticket["id"], status="escalated", priority="high",
                escalation_reason=reason,
            )
            draft = await storage.create_draft(
                tenant_id, email_id=email_id, ticket_id=ticket["id"],
                content=content, status="pending", auto=False, confidence=confidence,
            )
            await storage.update_email(tenant_id, email_id, status="escalated")
            await storage.log_decision(
                tenant_id, email_id=email_id, event="escalated",
                detail={"reason": reason, "rule": rule},
            )
            return {"action": "escalated", "draft_id": draft["id"], "ticket_id": ticket["id"]}

        content = (greeting + (triage.get("draft_body") or _NO_MATCH_BODY) + _SIGNATURE).strip()

        # 4: autosvar — bara om regeln säger auto OCH säkerhetsvillkoren håller.
        # ALLOW_AUTO_SEND är en hård global spärr: under pilot ska inget lämna
        # systemet utan mänskligt godkännande, oavsett hur reglerna är satta.
        auto_ok = (
            settings.allow_auto_send
            and rule == "auto"
            and confidence >= settings.auto_send_min_confidence
            and (sentiment is None or sentiment >= 0.4)
        )
        if rule == "auto" and not settings.allow_auto_send:
            await storage.log_decision(
                tenant_id,
                email_id=email_id,
                event="auto_send_blocked",
                detail={
                    "rule": rule,
                    "note": "ALLOW_AUTO_SEND är av — svaret lades som utkast för godkännande.",
                },
            )
        if auto_ok:
            from .sender import send_reply

            sent, result = await send_reply(
                to_email=email["from_email"],
                subject=email["subject"] or "Ditt ärende",
                body=content,
                in_reply_to=email.get("provider_message_id"),
            )
            if sent:
                draft = await storage.create_draft(
                    tenant_id, email_id=email_id, ticket_id=ticket["id"],
                    content=content, status="auto_sent", auto=True, confidence=confidence,
                )
                await storage.save_message(
                    tenant_id, conversation_id=ticket["conversation_id"],
                    direction="outbound", content=content,
                )
                await storage.update_ticket(tenant_id, ticket["id"], status="resolved")
                await storage.update_email(tenant_id, email_id, status="auto_sent")
                await storage.log_decision(
                    tenant_id, email_id=email_id, event="auto_sent",
                    detail={"rule": rule, "confidence": confidence, "note": f"Skickat ({result})."},
                )
                return {"action": "auto_sent", "draft_id": draft["id"], "ticket_id": ticket["id"]}
            # Sändningen failade — falla tillbaka på utkast så ärendet inte tappas.
            await storage.log_decision(
                tenant_id, email_id=email_id, event="send_failed",
                detail={"error": result, "note": "Autosvaret lades som utkast i stället."},
            )

        # 5: default — utkast som väntar på godkännande.
        draft = await storage.create_draft(
            tenant_id, email_id=email_id, ticket_id=ticket["id"],
            content=content, status="pending", auto=False, confidence=confidence,
        )
        await storage.update_email(tenant_id, email_id, status="awaiting_approval")
        await storage.log_decision(
            tenant_id, email_id=email_id, event="draft_created",
            detail={
                "rule": rule, "confidence": confidence,
                "why_not_auto": (
                    "Regeln är 'draft' — svaret kräver godkännande" if rule != "auto"
                    else "Autoskick är avstängt globalt (ALLOW_AUTO_SEND)"
                    if not settings.allow_auto_send
                    else f"Konfidens {confidence} under tröskeln {settings.auto_send_min_confidence}"
                    if confidence < settings.auto_send_min_confidence
                    else "Negativt sentiment — lämnas till människa"
                ),
            },
        )
        return {"action": "draft_created", "draft_id": draft["id"], "ticket_id": ticket["id"]}

    except Exception as error:  # noqa: BLE001 — ett trasigt mail får inte stoppa kön
        logger.exception("Processering av mail %s misslyckades", email_id)
        await storage.update_email(tenant_id, email_id, status="failed")
        await storage.log_decision(
            tenant_id, email_id=email_id, event="failed", detail={"error": str(error)},
        )
        return {"action": "failed", "error": str(error)}
