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

# Fack som får svara på varandras frågor. Enbart 'ovrigt' är avsiktligt tomt:
# en allmän fråga besvaras av en allmän artikel, men en allmän artikel duger
# ALDRIG som svar på ett tekniskt fel, en garantifråga eller en reklamation.
_COMPATIBLE_CATEGORIES: dict[str, set[str]] = {
    "garanti": {"garanti", "retur_reklamation"},
    "retur_reklamation": {"retur_reklamation", "garanti"},
}


def article_in_category(articles: list[dict], category: str) -> dict | None:
    """Bäst rankade artikeln som faktiskt hör till ärendets fack.

    Returnerar None när ingen träff gör det — då finns inget underlag att svara
    utifrån, oavsett hur högt sökningen råkade ranka något annat.
    """
    allowed = _COMPATIBLE_CATEGORIES.get(category, {category})
    for article in articles:
        if article.get("category") in allowed:
            return article
    return None


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

    # Sökningen är nyckelordsbaserad i simuleringsläge och matchar på ord som
    # förekommer i nästan varje artikel ("hjärtstartare"). Den bäst rankade
    # träffen kan därför handla om något helt annat än frågan: ett larm om att
    # utrustningen inte fungerar besvarades tidigare med bolagets kursutbud,
    # eftersom den artikeln råkade dela flest ord med meddelandet.
    #
    # Kravet är därför inte "fanns någon träff" utan "fanns underlag i det fack
    # ärendet tillhör". Saknas det lämnar vi över till en människa — samma
    # princip som grundningsregeln i övrigt: en lucka är alltid rätt, en gissning
    # alltid fel.
    grounded = article_in_category(articles, triage["category"])

    if escalated:
        reply_body = _ESCALATION_REPLY
    elif not articles:
        escalated = True
        escalation_reason = "Ingen träff i kunskapsbasen — svar lämnas till människa."
        reply_body = _NO_MATCH_REPLY
    elif grounded is None:
        escalated = True
        escalation_reason = (
            f"Kunskapsbasen saknar underlag om "
            f"{CATEGORY_LABELS[triage['category']].lower()} — träffarna handlar om "
            "något annat. Svar lämnas till människa."
        )
        reply_body = _NO_MATCH_REPLY
        # Träffar i fel fack är inte källor till något svar och ska inte
        # presenteras som om de vore det.
        articles = []
    else:
        top = grounded
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
        # Artikeln svaret faktiskt bygger på ligger först. UI:t visar "Källa: X"
        # och skulle annars kunna peka ut en artikel som inte användes, bara för
        # att sökningen råkade ranka den högst.
        "kb_sources": [
            {"title": a["title"], "similarity": a["similarity"]}
            for a in sorted(articles, key=lambda a: a is not grounded)
        ],
        "returning_customer": len(history) > 0,
        "simulation": True,
    }
