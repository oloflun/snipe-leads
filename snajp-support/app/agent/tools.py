"""Agentens verktyg — speglar referensarkitekturens funktionsverktyg.

Alla verktyg arbetar mot lagringslagret via SupportContext och registrerar
nyckelvärden (ticket_id, category, sentiment, eskalering) i kontexten så att
API-svaret kan byggas efter körningen.
"""

import json

from agents import RunContextWrapper, function_tool

from ..config import CATEGORIES
from .context import SupportContext


@function_tool
async def find_or_create_customer(
    ctx: RunContextWrapper[SupportContext], name: str | None = None
) -> str:
    """Identifiera kunden via e-post/telefon eller skapa en ny kundpost.

    Args:
        name: Kundens namn om det framgår av meddelandet.
    """
    support = ctx.context
    customer = await support.storage.find_or_create_customer(
        support.tenant_id,
        email=support.customer_email,
        phone=None,
        name=name or support.customer_name,
    )
    support.customer_id = customer["id"]
    history = await support.storage.get_customer_history(support.tenant_id, customer["id"])
    support.returning_customer = len(history) > 0
    return json.dumps(
        {"customer_id": customer["id"], "name": customer.get("name"),
         "previous_tickets": len(history)},
        ensure_ascii=False,
    )


@function_tool
async def create_ticket(
    ctx: RunContextWrapper[SupportContext], subject: str, category: str, priority: str = "normal"
) -> str:
    """Öppna ett supportärende i rätt fack.

    Args:
        subject: Kort ärenderubrik på svenska.
        category: Ett av: teknisk_support, leverans, betalning, retur_reklamation, konto, ovrigt.
        priority: low, normal eller high.
    """
    support = ctx.context
    if category not in CATEGORIES:
        category = "ovrigt"
    if not support.customer_id:
        return json.dumps({"error": "Anropa find_or_create_customer först."})
    ticket = await support.storage.create_ticket(
        support.tenant_id,
        customer_id=support.customer_id,
        subject=subject,
        category=category,
        channel=support.channel,
        priority=priority,
    )
    support.ticket_id = ticket["id"]
    support.conversation_id = ticket["conversation_id"]
    support.category = category
    return json.dumps({"ticket_id": ticket["id"], "category": category}, ensure_ascii=False)


@function_tool
async def save_inbound_message(
    ctx: RunContextWrapper[SupportContext], content: str, sentiment: float
) -> str:
    """Spara kundens inkommande meddelande med sentimentbedömning.

    Args:
        content: Kundens meddelande.
        sentiment: 0.0 (mycket upprörd) till 1.0 (mycket nöjd).
    """
    support = ctx.context
    if not support.conversation_id:
        return json.dumps({"error": "Anropa create_ticket först."})
    sentiment = max(0.0, min(1.0, sentiment))
    support.sentiment = sentiment
    await support.storage.save_message(
        support.tenant_id,
        conversation_id=support.conversation_id,
        direction="inbound",
        content=content,
        sentiment=sentiment,
        has_image=support.has_image,
    )
    return json.dumps({"saved": True, "sentiment": sentiment})


@function_tool
async def search_knowledge_base(ctx: RunContextWrapper[SupportContext], query: str) -> str:
    """Sök hjälpartiklar semantiskt i kunskapsbasen.

    Args:
        query: Sökfråga på svenska baserad på kundens ärende.
    """
    support = ctx.context
    embedding = None
    try:
        from .embeddings import embed_text

        embedding = await embed_text(query)
    except Exception:
        embedding = None
    articles = await support.storage.search_kb(support.tenant_id, query, embedding=embedding)
    support.kb_sources = [
        {"title": a["title"], "similarity": a["similarity"]} for a in articles
    ]
    if not articles:
        return json.dumps(
            {"results": [], "instruction": "Ingen träff — du MÅSTE eskalera till människa."},
            ensure_ascii=False,
        )
    return json.dumps({"results": articles}, ensure_ascii=False)


@function_tool
async def escalate_to_human(ctx: RunContextWrapper[SupportContext], reason: str) -> str:
    """Eskalera ärendet till en mänsklig handläggare.

    Args:
        reason: Tydlig svensk motivering till eskaleringen.
    """
    support = ctx.context
    support.escalated = True
    support.escalation_reason = reason
    if support.ticket_id:
        await support.storage.update_ticket(
            support.tenant_id,
            support.ticket_id,
            status="escalated",
            priority="high",
            escalation_reason=reason,
        )
    return json.dumps({"escalated": True, "reason": reason}, ensure_ascii=False)


@function_tool
async def send_response(ctx: RunContextWrapper[SupportContext], reply: str) -> str:
    """Skicka det färdiga svaret till kunden (anpassas efter kanalens maxlängd).

    Args:
        reply: Det fullständiga svenska svaret till kunden.
    """
    support = ctx.context
    config = await support.storage.get_channel_config(support.tenant_id, support.channel)
    if len(reply) > config["max_length"]:
        reply = reply[: config["max_length"] - 1].rstrip() + "…"
    support.final_reply = reply
    if support.conversation_id:
        await support.storage.save_message(
            support.tenant_id,
            conversation_id=support.conversation_id,
            direction="outbound",
            content=reply,
            sentiment=None,
            has_image=False,
        )
    return json.dumps({"sent": True, "length": len(reply)})


@function_tool
async def log_metric(
    ctx: RunContextWrapper[SupportContext], metric_name: str, value: float
) -> str:
    """Logga ett mätvärde för ärendet (t.ex. sentiment).

    Args:
        metric_name: Mätvärdets namn.
        value: Numeriskt värde.
    """
    support = ctx.context
    await support.storage.log_metric(
        support.tenant_id, ticket_id=support.ticket_id, metric_name=metric_name, value=value
    )
    return json.dumps({"logged": True})


ALL_TOOLS = [
    find_or_create_customer,
    create_ticket,
    save_inbound_message,
    search_knowledge_base,
    escalate_to_human,
    send_response,
    log_metric,
]
