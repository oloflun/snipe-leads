"""Simuleringsagenten: kör hela referens-workflowen mot riktig lagring,
men ersätter LLM-stegen med deterministiska svenska svar.

Workflow (identisk ordning som den riktiga agenten):
identifiera kund → skapa ärende (med fack) → spara inkommande meddelande med
sentiment → sök kunskapsbasen → formulera grundat svar (eller eskalera) →
spara utgående svar → logga metrics.
"""

from typing import Any

from ..config import CATEGORY_LABELS
from ..storage.base import Storage
from .sim_triage import classify

_VISION_NOTES = {
    "teknisk_support": (
        "Jag har tittat på din bifogade bild och ser en skärmdump med ett felmeddelande. "
    ),
    "retur_reklamation": (
        "Jag har tittat på din bifogade bild och ser skadan på varan/förpackningen. "
    ),
    "default": "Jag har tittat på din bifogade bild och tagit med den i bedömningen. ",
}

_GREETING = "Hej{name}!\n\n"

_ESCALATION_REPLY = (
    "Tack för ditt meddelande. Jag förstår att det här är viktigt, och den här typen av "
    "ärende hanteras alltid av en av mina mänskliga kollegor. Jag har öppnat ett ärende "
    "med hög prioritet och skickat vidare all information — du får svar från vår "
    "kundtjänst så snart som möjligt, senast inom en vardag."
)

_NO_MATCH_REPLY = (
    "Tack för ditt meddelande. Jag hittar tyvärr inget säkert svar på din fråga i vår "
    "kunskapsbas, och jag gissar aldrig. Jag har därför skickat ärendet vidare till en "
    "kollega som återkommer till dig så snart som möjligt."
)


def _first_name(name: str | None) -> str:
    if not name:
        return ""
    return " " + name.strip().split()[0]


async def run_sim_agent(
    storage: Storage,
    tenant_id: str,
    *,
    message: str,
    subject: str,
    channel: str,
    customer_email: str | None,
    customer_name: str | None,
    has_image: bool,
) -> dict[str, Any]:
    triage = classify(subject or "", message)

    customer = await storage.find_or_create_customer(
        tenant_id, email=customer_email, phone=None, name=customer_name
    )
    history = await storage.get_customer_history(tenant_id, customer["id"])

    ticket = await storage.create_ticket(
        tenant_id,
        customer_id=customer["id"],
        subject=subject or message[:80],
        category=triage["category"],
        channel=channel,
        priority=triage["priority"],
    )
    conversation_id = ticket["conversation_id"]

    await storage.save_message(
        tenant_id,
        conversation_id=conversation_id,
        direction="inbound",
        content=message,
        sentiment=triage["sentiment"],
        has_image=has_image,
    )

    articles = await storage.search_kb(tenant_id, f"{subject} {message}".strip())

    vision_note = ""
    if has_image:
        vision_note = _VISION_NOTES.get(triage["category"], _VISION_NOTES["default"])

    greeting = _GREETING.format(name=_first_name(customer_name))

    escalated = triage["escalate"]
    escalation_reason = triage["escalation_reason"]

    if escalated:
        reply_body = _ESCALATION_REPLY
    elif not articles:
        escalated = True
        escalation_reason = "Ingen träff i kunskapsbasen — svar lämnas till människa."
        reply_body = _NO_MATCH_REPLY
    else:
        top = articles[0]
        reply_body = (
            f"Tack för att du hör av dig om {CATEGORY_LABELS[triage['category']].lower()}. "
            f"{vision_note}Så här fungerar det hos oss:\n\n{top['content']}\n\n"
            "Hör gärna av dig igen om något är oklart — jag hjälper dig gärna vidare."
        )

    if escalated:
        await storage.update_ticket(
            tenant_id,
            ticket["id"],
            status="escalated",
            priority="high",
            escalation_reason=escalation_reason,
        )
        if has_image:
            reply_body = vision_note + reply_body

    config = await storage.get_channel_config(tenant_id, channel)
    reply = (greeting + reply_body).strip()
    if len(reply) > config["max_length"]:
        reply = reply[: config["max_length"] - 1].rstrip() + "…"

    await storage.save_message(
        tenant_id,
        conversation_id=conversation_id,
        direction="outbound",
        content=reply,
        sentiment=None,
        has_image=False,
    )
    await storage.log_metric(
        tenant_id, ticket_id=ticket["id"], metric_name="sentiment", value=triage["sentiment"]
    )
    await storage.log_metric(
        tenant_id, ticket_id=ticket["id"], metric_name="escalated", value=1.0 if escalated else 0.0
    )

    return {
        "reply": reply,
        "ticket_id": ticket["id"],
        "customer_id": customer["id"],
        "category": triage["category"],
        "category_label": triage["category_label"],
        "sentiment": triage["sentiment"],
        "escalated": escalated,
        "escalation_reason": escalation_reason,
        "kb_sources": [
            {"title": a["title"], "similarity": a["similarity"]} for a in articles
        ],
        "returning_customer": len(history) > 0,
        "simulation": True,
    }
