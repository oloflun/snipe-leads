"""Postgres-lagring mot Supabase (multi-tenant, pgvector + svensk fulltext-fallback).

Varje operation körs i en transaktion som först sätter app.tenant_id via
set_config — då verkställs RLS-policyerna från 003_snajp_multitenant.sql —
och varje query filtrerar dessutom explicit på tenant_id (försvar-på-djupet).

Vektorsökningen använder cosine-operatorn `<=>` med tröskel 0.25 och topp 3,
precis som referensarkitekturen. Saknas embeddings används
`websearch_to_tsquery('swedish', ...)` som fallback.
"""

import hashlib
import json
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from .base import status_transition_allowed


async def _init_connection(conn: asyncpg.Connection) -> None:
    # pgvector skickas som text: '[0.1,0.2,...]'
    await conn.set_type_codec(
        "vector",
        encoder=lambda v: json.dumps(v, separators=(",", ":")),
        decoder=lambda v: json.loads(v),
        schema="public",
        format="text",
    )


def _row(record: asyncpg.Record | None) -> dict[str, Any] | None:
    if record is None:
        return None
    data = dict(record)
    for key, value in data.items():
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        elif key == "id" or key.endswith("_id"):
            data[key] = str(value) if value is not None else None
        elif key == "sentiment" and value is not None:
            data[key] = float(value)
    return data


class PostgresStorage:
    name = "postgres"

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    @classmethod
    async def connect(cls, database_url: str) -> "PostgresStorage":
        pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=5,
            init=_init_connection,
            statement_cache_size=0,  # krävs bakom Supabase transaction pooler
        )
        return cls(pool)

    @asynccontextmanager
    async def _scoped(self, tenant_id: str):
        """Transaktion med app.tenant_id satt, så RLS-policyerna gäller."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.fetchval(
                    "select set_config('app.tenant_id', $1, true)", tenant_id
                )
                yield conn

    # -- Tenants ------------------------------------------------------------

    async def create_tenant(self, *, slug: str, name: str) -> dict[str, Any]:
        # Administrativ operation — körs utan tenant-kontext (kräver master-nyckel i API-lagret).
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                insert into ss_tenants (slug, name) values ($1, $2)
                on conflict (slug) do update set name = excluded.name
                returning *
                """,
                slug,
                name,
            )
        return _row(record)

    async def ensure_tenant(
        self, tenant_id: str, *, slug: str, name: str
    ) -> dict[str, Any]:
        # Administrativ operation — körs utan tenant-kontext.
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                insert into ss_tenants (id, slug, name) values ($1::uuid, $2, $3)
                on conflict (id) do update set name = excluded.name
                returning *
                """,
                tenant_id,
                slug,
                name,
            )
        return _row(record)

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow("select * from ss_tenants where id = $1", tenant_id)
        return _row(record)

    async def update_tenant(
        self,
        tenant_id: str,
        *,
        name: str | None = None,
        company_name: str | None = None,
        tone: str | None = None,
        system_prompt_extra: str | None = None,
    ) -> dict[str, Any] | None:
        # coalesce => None lämnar kolumnen orörd, tom sträng nollställer den.
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                update ss_tenants set
                  name = coalesce($2, name),
                  company_name = coalesce($3, company_name),
                  tone = coalesce($4, tone),
                  system_prompt_extra = coalesce($5, system_prompt_extra),
                  updated_at = now()
                where id = $1
                returning *
                """,
                tenant_id,
                name,
                company_name,
                tone,
                system_prompt_extra,
            )
        return _row(record)

    # -- Kunddata -----------------------------------------------------------

    async def find_or_create_customer(
        self, tenant_id: str, *, email: str | None, phone: str | None, name: str | None
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            for id_type, value in (("email", email), ("phone", phone)):
                if not value:
                    continue
                record = await conn.fetchrow(
                    """
                    select c.* from ss_customers c
                    join ss_customer_identifiers i on i.customer_id = c.id
                    where c.tenant_id = $1 and i.tenant_id = $1
                      and i.type = $2 and lower(i.value) = lower($3)
                    """,
                    tenant_id,
                    id_type,
                    value,
                )
                if record:
                    return _row(record)
            customer = await conn.fetchrow(
                "insert into ss_customers (tenant_id, name) values ($1, $2) returning *",
                tenant_id,
                name,
            )
            for id_type, value in (("email", email), ("phone", phone)):
                if value:
                    await conn.execute(
                        """
                        insert into ss_customer_identifiers (tenant_id, customer_id, type, value)
                        values ($1, $2, $3, lower($4)) on conflict do nothing
                        """,
                        tenant_id,
                        customer["id"],
                        id_type,
                        value,
                    )
            return _row(customer)

    async def get_customer_history(
        self, tenant_id: str, customer_id: str
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from ss_tickets
                where tenant_id = $1 and customer_id = $2
                order by created_at desc limit 20
                """,
                tenant_id,
                customer_id,
            )
        return [_row(r) for r in records]

    async def create_ticket(
        self,
        tenant_id: str,
        *,
        customer_id: str,
        subject: str,
        category: str,
        channel: str,
        priority: str = "normal",
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            ticket = await conn.fetchrow(
                """
                insert into ss_tickets (tenant_id, customer_id, subject, category, channel, priority)
                values ($1, $2, $3, $4, $5, $6) returning *
                """,
                tenant_id,
                customer_id,
                subject,
                category,
                channel,
                priority,
            )
            conversation = await conn.fetchrow(
                "insert into ss_conversations (tenant_id, ticket_id, channel) values ($1, $2, $3) returning *",
                tenant_id,
                ticket["id"],
                channel,
            )
        result = _row(ticket)
        result["conversation_id"] = str(conversation["id"])
        return result

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            ticket = await conn.fetchrow(
                "select * from ss_tickets where tenant_id = $1 and id = $2",
                tenant_id,
                ticket_id,
            )
            if not ticket:
                return None
            conversation = await conn.fetchrow(
                "select id from ss_conversations where tenant_id = $1 and ticket_id = $2",
                tenant_id,
                ticket_id,
            )
            messages = []
            if conversation:
                messages = await conn.fetch(
                    """
                    select * from ss_messages
                    where tenant_id = $1 and conversation_id = $2
                    order by created_at
                    """,
                    tenant_id,
                    conversation["id"],
                )
        result = _row(ticket)
        result["conversation_id"] = str(conversation["id"]) if conversation else None
        result["messages"] = [_row(m) for m in messages]
        return result

    async def update_ticket(
        self,
        tenant_id: str,
        ticket_id: str,
        *,
        status: str | None = None,
        category: str | None = None,
        priority: str | None = None,
        escalation_reason: str | None = None,
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            current = await conn.fetchrow(
                "select * from ss_tickets where tenant_id = $1 and id = $2",
                tenant_id,
                ticket_id,
            )
            if not current:
                return None
            new_status = current["status"]
            if status and status_transition_allowed(current["status"], status):
                new_status = status
            record = await conn.fetchrow(
                """
                update ss_tickets set
                  status = $3,
                  category = coalesce($4, category),
                  priority = coalesce($5, priority),
                  escalation_reason = coalesce($6, escalation_reason),
                  updated_at = now()
                where tenant_id = $1 and id = $2 returning *
                """,
                tenant_id,
                ticket_id,
                new_status,
                category,
                priority,
                escalation_reason,
            )
        return _row(record)

    async def save_message(
        self,
        tenant_id: str,
        *,
        conversation_id: str,
        direction: str,
        content: str,
        sentiment: float | None = None,
        has_image: bool = False,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            owner = await conn.fetchval(
                "select tenant_id from ss_conversations where id = $1", conversation_id
            )
            if owner is None or str(owner) != tenant_id:
                raise ValueError("Konversationen tillhör inte denna tenant.")
            record = await conn.fetchrow(
                """
                insert into ss_messages (tenant_id, conversation_id, direction, content, sentiment, has_image)
                values ($1, $2, $3, $4, $5, $6) returning *
                """,
                tenant_id,
                conversation_id,
                direction,
                content,
                sentiment,
                has_image,
            )
        return _row(record)

    async def get_messages(
        self, tenant_id: str, conversation_id: str
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from ss_messages
                where tenant_id = $1 and conversation_id = $2
                order by created_at
                """,
                tenant_id,
                conversation_id,
            )
        return [_row(r) for r in records]

    # -- Kunskapsbas --------------------------------------------------------

    async def search_kb(
        self,
        tenant_id: str,
        query: str,
        embedding: list[float] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            if embedding is not None:
                # Standardinställningen skannar bara ett kluster och missar artiklar.
                await conn.execute("set local ivfflat.probes = 10")
                records = await conn.fetch(
                    """
                    select id, title, content, category,
                           1 - (embedding <=> $2::vector) as similarity
                    from ss_knowledge_base
                    where tenant_id = $1 and embedding is not null
                    order by embedding <=> $2::vector
                    limit $3
                    """,
                    tenant_id,
                    embedding,
                    limit,
                )
                return [
                    {**_row(r), "similarity": round(float(r["similarity"]), 2)}
                    for r in records
                    if float(r["similarity"]) >= 0.25
                ]
            records = await conn.fetch(
                """
                select id, title, content, category,
                       ts_rank(search_tsv, websearch_to_tsquery('swedish', $2)) as rank
                from ss_knowledge_base
                where tenant_id = $1 and search_tsv @@ websearch_to_tsquery('swedish', $2)
                order by rank desc
                limit $3
                """,
                tenant_id,
                query,
                limit,
            )
        return [
            {"id": str(r["id"]), "title": r["title"], "content": r["content"],
             "category": r["category"], "similarity": round(float(r["rank"]), 2)}
            for r in records
        ]

    async def list_kb(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select id, title, content, category, created_at
                from ss_knowledge_base where tenant_id = $1 order by created_at
                """,
                tenant_id,
            )
        return [_row(r) for r in records]

    async def add_kb_article(
        self,
        tenant_id: str,
        *,
        title: str,
        content: str,
        category: str,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_knowledge_base (tenant_id, title, content, category, embedding)
                values ($1, $2, $3, $4, $5) returning id, title, category
                """,
                tenant_id,
                title,
                content,
                category,
                embedding,
            )
        return _row(record)

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
        # tenant_id i where-satsen gör att en artikel hos en annan tenant inte
        # bara nekas — den existerar inte ur den här tenantens synvinkel.
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                update ss_knowledge_base set
                  title = coalesce($3, title),
                  content = coalesce($4, content),
                  category = coalesce($5, category),
                  embedding = coalesce($6::vector, embedding),
                  -- Redigerad text är inte längre mallens platshållare.
                  is_placeholder = case when $4::text is null then is_placeholder else false end
                where id = $2 and tenant_id = $1
                returning id, title, content, category
                """,
                tenant_id,
                article_id,
                title,
                content,
                category,
                embedding,
            )
        return _row(record)

    async def delete_kb_article(self, tenant_id: str, article_id: str) -> bool:
        async with self._scoped(tenant_id) as conn:
            result = await conn.execute(
                "delete from ss_knowledge_base where id = $2 and tenant_id = $1",
                tenant_id,
                article_id,
            )
        return result.endswith(" 1")

    # -- Kanaler & metrics --------------------------------------------------

    async def get_channel_config(self, tenant_id: str, channel: str) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            # Tenant-specifik rad vinner; annars global default (tenant_id is null).
            record = await conn.fetchrow(
                """
                select * from ss_channel_configs
                where channel = $2 and (tenant_id = $1 or tenant_id is null)
                order by tenant_id nulls last limit 1
                """,
                tenant_id,
                channel,
            )
            if not record:
                record = await conn.fetchrow(
                    """
                    select * from ss_channel_configs
                    where channel = 'web' and tenant_id is null limit 1
                    """
                )
        return _row(record) or {"channel": "web", "tone": "halvformell", "max_length": 1500}

    async def log_metric(
        self, tenant_id: str, *, ticket_id: str | None, metric_name: str, value: float | None
    ) -> None:
        async with self._scoped(tenant_id) as conn:
            await conn.execute(
                """
                insert into ss_agent_metrics (tenant_id, ticket_id, metric_name, value)
                values ($1, $2, $3, $4)
                """,
                tenant_id,
                ticket_id,
                metric_name,
                value,
            )

    # -- Förbrukning ----------------------------------------------------------

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
    ) -> None:
        async with self._scoped(tenant_id) as conn:
            await conn.execute(
                """
                insert into ss_usage (
                  tenant_id, kind, model, simulated, prompt_tokens,
                  completion_tokens, total_tokens, responses, ticket_id, email_id
                ) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                tenant_id,
                kind,
                model,
                simulated,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                responses,
                ticket_id,
                email_id,
            )

    async def get_usage(self, tenant_id: str, *, days: int = 30) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            total = await conn.fetchrow(
                """
                select
                  coalesce(sum(responses), 0) as responses,
                  coalesce(sum(prompt_tokens), 0) as prompt_tokens,
                  coalesce(sum(completion_tokens), 0) as completion_tokens,
                  coalesce(sum(total_tokens), 0) as total_tokens,
                  coalesce(sum(responses) filter (where simulated), 0) as simulated_responses
                from ss_usage
                where tenant_id = $1 and created_at >= now() - ($2 || ' days')::interval
                """,
                tenant_id,
                str(days),
            )
            per_kind = await conn.fetch(
                """
                select kind,
                       coalesce(sum(responses), 0) as responses,
                       coalesce(sum(total_tokens), 0) as total_tokens
                from ss_usage
                where tenant_id = $1 and created_at >= now() - ($2 || ' days')::interval
                group by kind order by kind
                """,
                tenant_id,
                str(days),
            )
        return {
            "days": days,
            "responses": int(total["responses"]),
            "prompt_tokens": int(total["prompt_tokens"]),
            "completion_tokens": int(total["completion_tokens"]),
            "total_tokens": int(total["total_tokens"]),
            "simulated_responses": int(total["simulated_responses"]),
            "per_kind": [
                {
                    "kind": r["kind"],
                    "responses": int(r["responses"]),
                    "total_tokens": int(r["total_tokens"]),
                }
                for r in per_kind
            ],
        }

    # -- Email-pipeline -------------------------------------------------------

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
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_emails
                  (tenant_id, provider, provider_message_id, from_email, from_name,
                   subject, body_text, received_at)
                values ($1, $2, $3, $4, $5, $6, $7, coalesce($8::timestamptz, now()))
                on conflict (tenant_id, provider_message_id) do nothing
                returning *
                """,
                tenant_id,
                provider,
                provider_message_id,
                from_email,
                from_name,
                subject,
                body_text,
                received_at,
            )
        return _row(record)

    async def list_emails(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select e.*,
                  (select row_to_json(c) from ss_classifications c
                   where c.email_id = e.id order by c.created_at desc limit 1) as classification,
                  (select row_to_json(d) from ss_drafts d
                   where d.email_id = e.id order by d.created_at desc limit 1) as draft,
                  (select count(*) from ss_email_attachments a where a.email_id = e.id) as attachment_count,
                  exists(select 1 from ss_email_attachments a
                         where a.email_id = e.id and a.is_image) as has_image
                from ss_emails e
                where e.tenant_id = $1
                  and ($2::text is null or e.status = $2)
                  and ($3::text is null or exists(
                        select 1 from ss_classifications c
                        where c.email_id = e.id and c.category = $3))
                  and ($4::text is null or
                       e.subject ilike '%' || $4 || '%' or e.body_text ilike '%' || $4 || '%'
                       or e.from_email ilike '%' || $4 || '%')
                order by e.received_at desc
                limit $5
                """,
                tenant_id,
                status,
                category,
                search,
                limit,
            )
        results = []
        for record in records:
            data = _row(record)
            for key in ("classification", "draft"):
                if isinstance(data.get(key), str):
                    data[key] = json.loads(data[key])
            results.append(data)
        return results

    async def get_email(self, tenant_id: str, email_id: str) -> dict[str, Any] | None:
        rows = await self.list_emails(tenant_id, limit=1000)
        email = next((e for e in rows if e["id"] == email_id), None)
        if not email:
            return None
        async with self._scoped(tenant_id) as conn:
            attachments = await conn.fetch(
                "select * from ss_email_attachments where tenant_id = $1 and email_id = $2",
                tenant_id,
                email_id,
            )
        email["attachments"] = [_row(a) for a in attachments]
        email["decisions"] = await self.list_decisions(tenant_id, email_id)
        return email

    async def update_email(
        self,
        tenant_id: str,
        email_id: str,
        *,
        status: str | None = None,
        ticket_id: str | None = None,
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                update ss_emails set
                  status = coalesce($3, status),
                  ticket_id = coalesce($4::uuid, ticket_id),
                  updated_at = now()
                where tenant_id = $1 and id = $2 returning *
                """,
                tenant_id,
                email_id,
                status,
                ticket_id,
            )
        return _row(record)

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
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_email_attachments
                  (tenant_id, email_id, filename, content_type, data_url, is_image, size_bytes)
                values ($1, $2, $3, $4, $5, $6, $7) returning *
                """,
                tenant_id,
                email_id,
                filename,
                content_type,
                data_url,
                is_image,
                size_bytes,
            )
        return _row(record)

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
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_classifications
                  (tenant_id, email_id, category, priority, sentiment, confidence,
                   escalate, escalation_reason, reasoning, kb_sources, model)
                values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11) returning *
                """,
                tenant_id,
                email_id,
                category,
                priority,
                sentiment,
                confidence,
                escalate,
                escalation_reason,
                reasoning,
                json.dumps(kb_sources, ensure_ascii=False),
                model,
            )
        return _row(record)

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
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_drafts
                  (tenant_id, email_id, ticket_id, content, status, auto, confidence)
                values ($1, $2, $3::uuid, $4, $5, $6, $7) returning *
                """,
                tenant_id,
                email_id,
                ticket_id,
                content,
                status,
                auto,
                confidence,
            )
        return _row(record)

    async def get_draft(self, tenant_id: str, draft_id: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                "select * from ss_drafts where tenant_id = $1 and id = $2",
                tenant_id,
                draft_id,
            )
        return _row(record)

    async def update_draft(
        self,
        tenant_id: str,
        draft_id: str,
        *,
        status: str | None = None,
        content: str | None = None,
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                update ss_drafts set
                  status = coalesce($3, status),
                  content = coalesce($4, content),
                  updated_at = now()
                where tenant_id = $1 and id = $2 returning *
                """,
                tenant_id,
                draft_id,
                status,
                content,
            )
        return _row(record)

    async def add_review(
        self,
        tenant_id: str,
        *,
        draft_id: str,
        action: str,
        edited_content: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_human_reviews (tenant_id, draft_id, action, edited_content, note)
                values ($1, $2, $3, $4, $5) returning *
                """,
                tenant_id,
                draft_id,
                action,
                edited_content,
                note,
            )
        return _row(record)

    async def get_category_rules(self, tenant_id: str) -> dict[str, str]:
        from ..config import DEFAULT_CATEGORY_RULES

        rules = dict(DEFAULT_CATEGORY_RULES)
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                "select category, mode from ss_category_rules where tenant_id = $1",
                tenant_id,
            )
        for record in records:
            rules[record["category"]] = record["mode"]
        return rules

    async def set_category_rule(self, tenant_id: str, category: str, mode: str) -> None:
        async with self._scoped(tenant_id) as conn:
            await conn.execute(
                """
                insert into ss_category_rules (tenant_id, category, mode)
                values ($1, $2, $3)
                on conflict (tenant_id, category) do update set mode = excluded.mode
                """,
                tenant_id,
                category,
                mode,
            )

    async def log_decision(
        self, tenant_id: str, *, email_id: str | None, event: str, detail: dict[str, Any]
    ) -> None:
        async with self._scoped(tenant_id) as conn:
            await conn.execute(
                """
                insert into ss_decision_log (tenant_id, email_id, event, detail)
                values ($1, $2::uuid, $3, $4::jsonb)
                """,
                tenant_id,
                email_id,
                event,
                json.dumps(detail, ensure_ascii=False),
            )

    async def list_decisions(
        self, tenant_id: str, email_id: str
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from ss_decision_log
                where tenant_id = $1 and email_id = $2 order by created_at
                """,
                tenant_id,
                email_id,
            )
        results = []
        for record in records:
            data = _row(record)
            if isinstance(data.get("detail"), str):
                data["detail"] = json.loads(data["detail"])
            results.append(data)
        return results

    # -- API-nycklar --------------------------------------------------------

    async def validate_api_key(self, raw_key: str) -> dict[str, Any] | None:
        # Körs INNAN tenant är känd — utan tenant-kontext (se api_key_lookup-policyn).
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                select k.*, t.active as tenant_active from ss_api_keys k
                join ss_tenants t on t.id = k.tenant_id
                where k.key_hash = $1 and k.active and k.revoked_at is null
                """,
                key_hash,
            )
            if record and record["tenant_active"]:
                await conn.execute(
                    "update ss_api_keys set last_used_at = now() where id = $1", record["id"]
                )
                return _row(record)
        return None

    async def create_api_key(
        self, tenant_id: str, *, tenant_name: str, raw_key: str, label: str | None = None
    ) -> dict[str, Any]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_api_keys (tenant_id, tenant_name, key_prefix, key_hash, label)
                values ($1, $2, $3, $4, $5)
                on conflict (key_hash) do update set active = true, revoked_at = null
                returning *
                """,
                tenant_id,
                tenant_name,
                raw_key[:12],
                key_hash,
                label,
            )
        return _row(record)

    async def list_api_keys(self, tenant_id: str) -> list[dict[str, Any]]:
        # key_hash utelämnas medvetet — den ska aldrig lämna lagringslagret.
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select id, label, key_prefix, active, revoked_at, created_at, last_used_at
                from ss_api_keys where tenant_id = $1 order by created_at desc
                """,
                tenant_id,
            )
        return [_row(r) for r in records]

    async def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        async with self._scoped(tenant_id) as conn:
            result = await conn.execute(
                """
                update ss_api_keys set active = false, revoked_at = now()
                where id = $2 and tenant_id = $1 and revoked_at is null
                """,
                tenant_id,
                key_id,
            )
        return result.endswith(" 1")

    async def close(self) -> None:
        await self.pool.close()
