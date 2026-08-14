"""Lagringsgränssnitt (multi-tenant).

Tabellstrukturen speglar referensarkitekturen (jawwad-ali/ai-customer-support-agent)
utökad med tenants: varje kunddatarad bär tenant_id och alla metoder tar tenant_id
som första parameter, så att varje kundföretag är helt isolerat. Två implementationer:

- PostgresStorage: Supabase Postgres + pgvector; sätter dessutom app.tenant_id per
  transaktion så RLS-policyerna i 003_snajp_multitenant.sql verkställs.
- MemoryStorage: in-memory med samma gränssnitt (graceful degradation utan databas).
"""

from typing import Any, Protocol


class Storage(Protocol):
    name: str

    # -- Tenants (administrativa; kräver master-nyckel i API-lagret) --------

    async def create_tenant(self, *, slug: str, name: str) -> dict[str, Any]: ...

    async def ensure_tenant(
        self, tenant_id: str, *, slug: str, name: str
    ) -> dict[str, Any]:
        """Skapar en tenant med FÖRUTBESTÄMT id om den saknas (idempotent)."""
        ...

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None: ...

    async def update_tenant(
        self,
        tenant_id: str,
        *,
        name: str | None = None,
        company_name: str | None = None,
        tone: str | None = None,
        system_prompt_extra: str | None = None,
    ) -> dict[str, Any] | None:
        """Tenantens egna inställningar (self-service). None = lämna oförändrad."""
        ...

    # -- Kunddata (alltid tenant-skopade) -----------------------------------

    async def find_or_create_customer(
        self, tenant_id: str, *, email: str | None, phone: str | None, name: str | None
    ) -> dict[str, Any]: ...

    async def get_customer_history(
        self, tenant_id: str, customer_id: str
    ) -> list[dict[str, Any]]: ...

    async def create_ticket(
        self,
        tenant_id: str,
        *,
        customer_id: str,
        subject: str,
        category: str,
        channel: str,
        priority: str = "normal",
    ) -> dict[str, Any]: ...

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> dict[str, Any] | None: ...

    async def update_ticket(
        self,
        tenant_id: str,
        ticket_id: str,
        *,
        status: str | None = None,
        category: str | None = None,
        priority: str | None = None,
        escalation_reason: str | None = None,
    ) -> dict[str, Any] | None: ...

    async def save_message(
        self,
        tenant_id: str,
        *,
        conversation_id: str,
        direction: str,
        content: str,
        sentiment: float | None = None,
        has_image: bool = False,
    ) -> dict[str, Any]: ...

    async def get_messages(
        self, tenant_id: str, conversation_id: str
    ) -> list[dict[str, Any]]: ...

    async def search_kb(
        self,
        tenant_id: str,
        query: str,
        embedding: list[float] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]: ...

    async def list_kb(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def add_kb_article(
        self,
        tenant_id: str,
        *,
        title: str,
        content: str,
        category: str,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]: ...

    async def update_kb_article(
        self,
        tenant_id: str,
        article_id: str,
        *,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        embedding: list[float] | None = None,
    ) -> dict[str, Any] | None:
        """None om artikeln inte finns ELLER tillhör en annan tenant."""
        ...

    async def delete_kb_article(self, tenant_id: str, article_id: str) -> bool: ...

    async def get_channel_config(self, tenant_id: str, channel: str) -> dict[str, Any]: ...

    async def log_metric(
        self, tenant_id: str, *, ticket_id: str | None, metric_name: str, value: float | None
    ) -> None: ...

    # -- Förbrukning (underlag för tak/fakturering) -------------------------

    async def log_usage(
        self,
        tenant_id: str,
        *,
        kind: str = "chat",
        model: str = "simulation",
        simulated: bool = False,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        responses: int = 1,
        ticket_id: str | None = None,
        email_id: str | None = None,
    ) -> None: ...

    async def get_usage(self, tenant_id: str, *, days: int = 30) -> dict[str, Any]:
        """Summering för perioden + uppdelning per kind."""
        ...

    async def count_responses_since(self, tenant_id: str, since: str) -> int:
        """Antal AI-svar sedan `since` (ISO-8601). Underlag för kvotkontrollen."""
        ...

    # -- Abonnemang (speglar Stripe) ----------------------------------------

    async def get_subscription(self, tenant_id: str) -> dict[str, Any] | None: ...

    async def upsert_subscription(
        self,
        tenant_id: str,
        *,
        plan_id: str | None = None,
        status: str | None = None,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        current_period_start: str | None = None,
        current_period_end: str | None = None,
        cancel_at_period_end: bool | None = None,
    ) -> dict[str, Any]: ...

    async def find_tenant_by_stripe_customer(self, customer_id: str) -> str | None:
        """Slår upp tenant INNAN tenant är känd — används av webhooken."""
        ...

    # -- Email-pipeline ------------------------------------------------------

    async def save_email(
        self,
        tenant_id: str,
        *,
        provider: str,
        provider_message_id: str,
        from_email: str,
        from_name: str | None,
        subject: str,
        body_text: str,
        received_at: str | None = None,
    ) -> dict[str, Any] | None:
        """Sparar ett inkommande mail. Returnerar None vid dublett (dedupe)."""
        ...

    async def list_emails(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    async def get_email(self, tenant_id: str, email_id: str) -> dict[str, Any] | None: ...

    async def update_email(
        self,
        tenant_id: str,
        email_id: str,
        *,
        status: str | None = None,
        ticket_id: str | None = None,
    ) -> dict[str, Any] | None: ...

    async def add_attachment(
        self,
        tenant_id: str,
        *,
        email_id: str,
        filename: str,
        content_type: str,
        data_url: str | None,
        is_image: bool,
        size_bytes: int = 0,
    ) -> dict[str, Any]: ...

    async def save_classification(
        self,
        tenant_id: str,
        *,
        email_id: str,
        category: str,
        priority: str,
        sentiment: float | None,
        confidence: float,
        escalate: bool,
        escalation_reason: str | None,
        reasoning: str,
        kb_sources: list[dict[str, Any]],
        model: str,
    ) -> dict[str, Any]: ...

    async def create_draft(
        self,
        tenant_id: str,
        *,
        email_id: str,
        ticket_id: str | None,
        content: str,
        status: str,
        auto: bool,
        confidence: float,
    ) -> dict[str, Any]: ...

    async def get_draft(self, tenant_id: str, draft_id: str) -> dict[str, Any] | None: ...

    async def update_draft(
        self,
        tenant_id: str,
        draft_id: str,
        *,
        status: str | None = None,
        content: str | None = None,
    ) -> dict[str, Any] | None: ...

    async def add_review(
        self,
        tenant_id: str,
        *,
        draft_id: str,
        action: str,
        edited_content: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]: ...

    async def get_category_rules(self, tenant_id: str) -> dict[str, str]: ...

    async def set_category_rule(self, tenant_id: str, category: str, mode: str) -> None: ...

    async def log_decision(
        self, tenant_id: str, *, email_id: str | None, event: str, detail: dict[str, Any]
    ) -> None: ...

    async def list_decisions(
        self, tenant_id: str, email_id: str
    ) -> list[dict[str, Any]]: ...

    # -- API-nycklar (validering sker INNAN tenant är känd) -----------------

    async def validate_api_key(self, raw_key: str) -> dict[str, Any] | None: ...

    async def create_api_key(
        self, tenant_id: str, *, tenant_name: str, raw_key: str, label: str | None = None
    ) -> dict[str, Any]: ...

    async def list_api_keys(self, tenant_id: str) -> list[dict[str, Any]]:
        """Tenantens egna nycklar — prefix och metadata, ALDRIG hash eller klartext."""
        ...

    async def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        """False om nyckeln inte finns ELLER tillhör en annan tenant."""
        ...

    async def close(self) -> None: ...


# Framåtriktade statusövergångar, som i referensrepot (forward-only).
STATUS_ORDER = ["open", "in_progress", "escalated", "resolved", "closed"]


def status_transition_allowed(current: str, new: str) -> bool:
    try:
        return STATUS_ORDER.index(new) >= STATUS_ORDER.index(current)
    except ValueError:
        return False
