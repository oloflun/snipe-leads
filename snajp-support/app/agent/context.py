"""Körningskontext som delas med agentens verktyg."""

from dataclasses import dataclass, field
from typing import Any

from ..storage.base import Storage


@dataclass
class SupportContext:
    storage: Storage
    tenant_id: str = ""
    channel: str = "web"
    customer_email: str | None = None
    customer_name: str | None = None
    subject: str = ""
    has_image: bool = False

    # Fylls i av verktygen under körningen
    customer_id: str | None = None
    ticket_id: str | None = None
    conversation_id: str | None = None
    category: str | None = None
    sentiment: float | None = None
    escalated: bool = False
    escalation_reason: str | None = None
    final_reply: str | None = None
    kb_sources: list[dict[str, Any]] = field(default_factory=list)
    returning_customer: bool = False
