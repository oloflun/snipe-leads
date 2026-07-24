"""Den riktiga Snajp-Support-agenten (OpenAI Agents SDK).

Modellen driver verktygsloopen själv — ingen handskriven iteration — precis
som i referensarkitekturen. Vision hanteras genom multimodala input-items
(input_image med data-URL) till gpt-4o-mini.
"""

from typing import Any

from agents import Agent, Runner

from ..config import get_settings
from ..storage.base import Storage
from .context import SupportContext
from .llm import get_agent_model
from .prompt import SYSTEM_PROMPT
from .tools import ALL_TOOLS


def build_agent(channel_tone: str, max_length: int) -> Agent[SupportContext]:
    instructions = (
        SYSTEM_PROMPT
        + f"\n## Aktuell kanal\nTon: {channel_tone}. Maxlängd på svaret: {max_length} tecken."
    )
    return Agent[SupportContext](
        name="Snajp-Support",
        instructions=instructions,
        model=get_agent_model(),
        tools=ALL_TOOLS,
    )


def _build_input(message: str, subject: str, attachments: list[str]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    text = message if not subject else f"Ämne: {subject}\n\n{message}"
    content.append({"type": "input_text", "text": text})
    # Vision stöds bara av OpenAI-modellerna; DeepSeek deepseek-chat är textbaserad.
    if attachments and get_settings().llm_provider == "openai":
        for data_url in attachments:
            content.append({"type": "input_image", "image_url": data_url, "detail": "auto"})
    elif attachments:
        content[0]["text"] += "\n\n[Bild bifogad — bildanalys stöds ej av nuvarande modell.]"
    return [{"role": "user", "content": content}]


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
    config = await storage.get_channel_config(tenant_id, channel)
    agent = build_agent(config["tone"], config["max_length"])
    context = SupportContext(
        storage=storage,
        tenant_id=tenant_id,
        channel=channel,
        customer_email=customer_email,
        customer_name=customer_name,
        subject=subject,
        has_image=bool(attachments),
    )

    result = await Runner.run(
        agent,
        _build_input(message, subject, attachments),
        context=context,
        max_turns=20,
    )

    # send_response är källan till kundsvaret; final_output är fallback.
    reply = context.final_reply or str(result.final_output or "").strip()
    if not reply:
        reply = (
            "Tack för ditt meddelande! Jag har öppnat ett ärende och en kollega "
            "återkommer till dig så snart som möjligt."
        )

    from ..config import CATEGORY_LABELS

    category = context.category or "ovrigt"
    return {
        "reply": reply,
        "ticket_id": context.ticket_id,
        "customer_id": context.customer_id,
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Övrigt"),
        "sentiment": context.sentiment,
        "escalated": context.escalated,
        "escalation_reason": context.escalation_reason,
        "kb_sources": context.kb_sources,
        "returning_customer": context.returning_customer,
        "simulation": False,
    }
