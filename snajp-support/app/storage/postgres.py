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


def _avkoda_jsonb(data: dict[str, Any] | None, *nycklar: str) -> dict[str, Any] | None:
    """jsonb-kolumner kommer tillbaka som TEXT från asyncpg.

    Utan en typkodare avkodar asyncpg varken json eller jsonb — värdet blir en
    sträng som SER rätt ut i en logg och i ett JSON-svar, och först konsumenten
    märker något. `step_log` nådde adminytans spårvy som en sträng, och sidan
    föll på `steps.map is not a function`; det syntes aldrig i sviten, eftersom
    MemoryStorage lämnar riktiga listor.

    Kodaren sätts INTE globalt i `_init_connection`: fyra anropsställen i den
    här filen avkodar redan för hand (`json.loads` med isinstance-vakt), och en
    global kodare hade gett dem en dict att köra json.loads på. Avkodningen bor
    därför där kolumnen läses, som redan är mönstret här.
    """
    if data is None:
        return None
    for nyckel in nycklar:
        if isinstance(data.get(nyckel), str):
            try:
                data[nyckel] = json.loads(data[nyckel])
            except (ValueError, TypeError):
                # Ett ovärderbart fält är bättre än en 500 i ett driftverktyg.
                pass
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

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow("select * from ss_tenants where id = $1", tenant_id)
        return _row(record)

    async def list_tenants(self) -> list[dict[str, Any]]:
        # Administrativ, körs utan tenant-kontext: pollern måste se alla tenants
        # för att kunna hämta post åt var och en. RLS-policyn tenant_lookup
        # tillåter select när app.tenant_id inte är satt.
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                "select * from ss_tenants where active order by created_at"
            )
        return [_row(r) for r in records]

    # -- Inkorgar -----------------------------------------------------------

    async def list_mailboxes(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select id, tenant_id, provider, address, status, imap_host,
                       last_sync_at, last_error
                from ss_mailboxes where tenant_id = $1 order by created_at
                """,
                tenant_id,
            )
        return [_row(r) for r in records]

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
                -- Tiebreakern gör radordningen DEFINIERAD. Utan andra
                -- sorteringsnyckel är ordningen mellan rader med samma
                -- created_at odefinierad i SQL, och support_agent plockar då
                -- fel tre ärenden ur history[:MAX_HISTORY_TICKETS].
                --
                -- Här räcker id, till skillnad från i MemoryStorage: exakt
                -- lika created_at kan bara uppstå för ärenden skapade i SAMMA
                -- transaktion (now() är transaktionens tidsstämpel), och varje
                -- ärende skapas i sin egen request. Ordningen mellan två
                -- sådana är godtycklig men stabil, vilket är tillräckligt —
                -- de är samtidiga och har ingen sann inbördes ordning.
                select * from ss_tickets
                where tenant_id = $1 and customer_id = $2
                order by created_at desc, id desc limit 20
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
            # websearch_to_tsquery ANDar alla ord. En riktig kundfråga innehåller
            # alltid "vad", "hur", "kommer" och liknande, så villkoret att SAMMA
            # artikel ska innehålla varje ord uppfylls i praktiken aldrig:
            # "frakt" gav 1 träff, men "Vad kostar frakten och hur snabbt kommer
            # varan?" gav 0. Fallbacken var alltså i praktiken död, och varje
            # fråga eskalerades så fort embeddings saknades.
            #
            # plainto_tsquery ANDar också, medan `|` mellan orden ger OR: minst
            # ett ord ska finnas, och ts_rank rangordnar efter hur många och hur
            # ovanliga de är. Ord som saknas i det svenska ordförrådet faller
            # bort av to_tsquery själv.
            records = await conn.fetch(
                """
                with q as (
                  select array_to_string(
                    array(
                      select lexeme from unnest(to_tsvector('swedish', $2))
                    ), ' | '
                  ) as expr
                )
                select k.id, k.title, k.content, k.category,
                       ts_rank(k.search_tsv, to_tsquery('swedish', q.expr)) as rank
                from ss_knowledge_base k, q
                where k.tenant_id = $1
                  and q.expr <> ''
                  and k.search_tsv @@ to_tsquery('swedish', q.expr)
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

    async def get_agent_taxonomy(self, tenant_id: str) -> tuple[str, ...]:
        from ..config import CATEGORIES  # undvik cirkulär import vid modulnivå

        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                select taxonomy from agent_configs
                where tenant_id = $1 and agent_type = 'support'
                """,
                tenant_id,
            )
        taxonomy = record["taxonomy"] if record else None
        return tuple(taxonomy) if taxonomy else CATEGORIES

    async def save_context_doc(
        self, tenant_id: str, *, kind: str, content: str, source: str = ""
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            existing = await conn.fetchval(
                "select max(version) from agent_context_docs where tenant_id = $1 and kind = $2",
                tenant_id,
                kind,
            )
            record = await conn.fetchrow(
                """
                insert into agent_context_docs (tenant_id, kind, content, source, version)
                values ($1, $2, $3, $4, $5) returning *
                """,
                tenant_id,
                kind,
                content,
                source,
                (existing or 0) + 1,
            )
        return _row(record)

    async def list_context_docs(
        self, tenant_id: str, *, kind: str | None = None
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            if kind:
                records = await conn.fetch(
                    """
                    select * from agent_context_docs where tenant_id = $1 and kind = $2
                    order by created_at desc
                    """,
                    tenant_id,
                    kind,
                )
            else:
                records = await conn.fetch(
                    "select * from agent_context_docs where tenant_id = $1 order by created_at desc",
                    tenant_id,
                )
        return [_row(r) for r in records]

    async def get_latest_context_doc(self, tenant_id: str, *, kind: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                select * from agent_context_docs where tenant_id = $1 and kind = $2
                order by version desc limit 1
                """,
                tenant_id,
                kind,
            )
        return _row(record)

    async def list_due_send_queue(self, tenant_id: str, now) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                "select * from send_queue where tenant_id = $1 and status = 'queued' and scheduled_at <= $2",
                tenant_id,
                now,
            )
        return [_row(r) for r in records]

    async def update_send_queue_status(
        self, tenant_id: str, item_id: str, *, status: str, gate_checks: dict[str, Any]
    ) -> None:
        async with self._scoped(tenant_id) as conn:
            await conn.execute(
                "update send_queue set status = $2, gate_checks = $3 where tenant_id = $1 and id = $4",
                tenant_id,
                status,
                json.dumps(gate_checks),
                item_id,
            )

    async def get_outreach_thread(self, tenant_id: str, thread_id: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                select t.*, p.contact_email as prospect_email, p.company_name
                from outreach_threads t
                left join prospects p on p.id = t.prospect_id
                where t.tenant_id = $1 and t.id = $2
                """,
                tenant_id,
                thread_id,
            )
        return _row(record)

    # -- Underlaget send_guard dömer på (DEL 2.3) ---------------------------
    # Spegelbild av MemoryStorage. Skiljer de sig åt är minnesvägen en lögn om
    # vad produktionen gör — precis den luckan som dolde agent_type-buggen.

    async def list_suppressions(self, tenant_id: str) -> set[str]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                "select email from suppressions where tenant_id = $1", tenant_id
            )
        return {str(r["email"]).strip().casefold() for r in records}

    async def add_suppression(self, tenant_id: str, *, email: str, reason: str) -> None:
        adress = str(email or "").strip().casefold()
        if not adress:
            raise ValueError("add_suppression kräver en e-postadress.")
        async with self._scoped(tenant_id) as conn:
            # workspace_id hämtas ur kopplingen; kolumnen är not null sedan 000.
            # Finns ingen workspace för tenanten är det ett riktigt fel — en
            # avregistrering som tyst inte sparas är det värsta utfallet här.
            await conn.execute(
                """
                insert into suppressions (workspace_id, tenant_id, email, reason)
                select w.id, $1, $2, $3
                  from workspaces w
                 where w.ss_tenant_id = $1
                on conflict do nothing
                """,
                tenant_id,
                adress,
                reason,
            )

    async def count_sent_outreach(self, tenant_id: str, *, since=None) -> int:
        async with self._scoped(tenant_id) as conn:
            return await conn.fetchval(
                """
                select count(*) from outreach_messages
                 where tenant_id = $1
                   and direction = 'outbound'
                   and sent_at is not null
                   and ($2::timestamptz is null or sent_at >= $2)
                """,
                tenant_id,
                since,
            )

    async def last_contact_with_company(self, tenant_id: str, foretagsnyckel: str):
        if not foretagsnyckel:
            return None
        async with self._scoped(tenant_id) as conn:
            return await conn.fetchval(
                """
                -- foretagsnyckel är en GENERERAD kolumn (migration 031). Att
                -- räkna fram den här också hade varit en andra uträkning av
                -- samma sak, alltså ett andra tillfälle att räkna fel.
                select max(m.sent_at)
                  from outreach_messages m
                  join outreach_threads t on t.id = m.thread_id
                  left join prospects p on p.id = t.prospect_id
                 where m.tenant_id = $1
                   and m.direction = 'outbound'
                   and m.sent_at is not null
                   and p.foretagsnyckel = $2
                """,
                tenant_id,
                foretagsnyckel,
            )

    async def get_pending_outreach_message(
        self, tenant_id: str, thread_id: str
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                select * from outreach_messages
                where tenant_id = $1 and thread_id = $2 and direction = 'outbound' and sent_at is null
                order by id limit 1
                """,
                tenant_id,
                thread_id,
            )
        return _row(record)

    async def mark_outreach_message_sent(self, tenant_id: str, message_id: str, sent_at) -> None:
        async with self._scoped(tenant_id) as conn:
            await conn.execute(
                "update outreach_messages set sent_at = $2 where tenant_id = $1 and id = $3",
                tenant_id,
                sent_at,
                message_id,
            )

    async def queue_outreach_message(
        self,
        tenant_id: str,
        *,
        thread_id: str,
        body: str,
        subject: str,
        humanizer_variant: str,
        scheduled_at,
        status: str = "queued",
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            message = await conn.fetchrow(
                """
                insert into outreach_messages
                  (tenant_id, thread_id, direction, body, subject, humanizer_variant, sent_at)
                values ($1, $2, 'outbound', $3, $4, $5, null)
                returning *
                """,
                tenant_id,
                thread_id,
                body,
                subject,
                humanizer_variant,
            )
            queue_item = await conn.fetchrow(
                """
                insert into send_queue (tenant_id, thread_id, scheduled_at, status, gate_checks)
                values ($1, $2, $3, $4, '{}'::jsonb)
                returning *
                """,
                tenant_id,
                thread_id,
                scheduled_at,
                status,
            )
        return {"message": _row(message), "queue_item": _row(queue_item)}

    async def create_prospect(
        self,
        tenant_id: str,
        *,
        company_name: str,
        contact_name: str | None = None,
        contact_email: str | None = None,
        origin: str = "manual",
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into prospects (tenant_id, company_name, contact_name, contact_email, origin)
                values ($1, $2, $3, $4, $5) returning *
                """,
                tenant_id,
                company_name,
                contact_name,
                contact_email,
                origin,
            )
        return _row(record)

    async def get_prospect(self, tenant_id: str, prospect_id: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                "select * from prospects where tenant_id = $1 and id = $2", tenant_id, prospect_id
            )
        return _row(record)

    async def list_prospects(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                "select * from prospects where tenant_id = $1 order by created_at desc limit $2",
                tenant_id,
                limit,
            )
        return [_row(r) for r in records]

    async def update_prospect(
        self,
        tenant_id: str,
        prospect_id: str,
        *,
        status: str | None = None,
        icp_fit: float | None = None,
        qualified: bool | None = None,
        disqualifiers: list[str] | None = None,
    ) -> dict[str, Any] | None:
        # Dynamisk SET-lista: en PATCH ska kunna sätta ETT fält utan att nolla
        # de andra, och en fast update-sats hade krävt att anroparen skickar
        # allt varje gång — vilket är hur en bedömning råkar skrivas över.
        updates = {
            "status": status,
            "icp_fit": icp_fit,
            "qualified": qualified,
            "disqualifiers": disqualifiers,
        }
        fields = {name: value for name, value in updates.items() if value is not None}
        if not fields:
            return await self.get_prospect(tenant_id, prospect_id)

        # Kolumnnamnen kommer ur dicten ovan, aldrig ur anroparen — värdena
        # går som parametrar.
        assignments = ", ".join(
            f"{name} = ${index}" for index, name in enumerate(fields, start=3)
        )
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                f"update prospects set {assignments} where tenant_id = $1 and id = $2 returning *",
                tenant_id,
                prospect_id,
                *fields.values(),
            )
        return _row(record)

    async def create_prospect_source(
        self,
        tenant_id: str,
        *,
        prospect_id: str,
        source_url: str,
        source_type: str,
        lawful_basis: str,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into prospect_sources (tenant_id, prospect_id, source_url, source_type, lawful_basis)
                values ($1, $2, $3, $4, $5) returning *
                """,
                tenant_id,
                prospect_id,
                source_url,
                source_type,
                lawful_basis,
            )
        return _row(record)

    async def list_prospect_source_urls(self, tenant_id: str, prospect_id: str) -> set[str]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                "select source_url from prospect_sources where tenant_id = $1 and prospect_id = $2",
                tenant_id,
                prospect_id,
            )
        return {r["source_url"] for r in records}

    async def log_agent_run(
        self,
        tenant_id: str,
        *,
        agent_type: str,
        pack_version: str,
        skills_used: list[str],
        input_text: str,
        output_text: str,
        step_log: list[dict[str, Any]],
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        # Default false och inte None: "vet inte" ska inte vara ett möjligt
        # tillstånd för om en körning räknas som kundvolym. Se migration 036.
        is_test: bool = False,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into agent_runs
                  (tenant_id, agent_type, pack_version, skills_used, input, output,
                   step_log, tokens_in, tokens_out, latency_ms, is_test)
                values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                returning *
                """,
                tenant_id,
                agent_type,
                pack_version,
                skills_used,
                input_text,
                output_text,
                json.dumps(step_log, ensure_ascii=False),
                tokens_in,
                tokens_out,
                latency_ms,
                is_test,
            )
        return _row(record)

    async def list_agent_runs(
        self, tenant_id: str, *, agent_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            if agent_type:
                records = await conn.fetch(
                    """select * from agent_runs where tenant_id = $1 and agent_type = $2
                       order by created_at desc limit $3""",
                    tenant_id,
                    agent_type,
                    limit,
                )
            else:
                records = await conn.fetch(
                    "select * from agent_runs where tenant_id = $1 order by created_at desc limit $2",
                    tenant_id,
                    limit,
                )
        return [_row(r) for r in records]

    async def list_skill_files(self, *, manifest_hash: str) -> list[dict[str, Any]]:
        # AVSIKTLIGT ingen _scoped(tenant_id): agent_skill_files har ingen
        # tenant_id-kolumn (migration 016, delad baselinekatalog). Det är
        # inte en glömd RLS-scoping — det finns inget att scopa på.
        async with self._pool.acquire() as conn:
            records = await conn.fetch(
                """select namespace, relative_path, content, sha256
                   from agent_skill_files where manifest_hash = $1""",
                manifest_hash,
            )
        return [_row(r) for r in records]

    async def publish_skill_files(
        self, *, manifest_hash: str, rows: list[dict[str, Any]], published_by: str = ""
    ) -> int:
        # snajp_app har REVOKE insert på tabellen (migration 016) — tjänsten
        # kan inte skriva om sina egna skills. Publicering körs därför med en
        # administrativ anslutning via scripts/publish_skills.py.
        async with self._pool.acquire() as conn:
            result = await conn.executemany(
                """insert into agent_skill_files
                     (manifest_hash, namespace, relative_path, content, sha256,
                      byte_size, published_by)
                   values ($1, $2, $3, $4, $5, $6, $7)
                   on conflict (manifest_hash, namespace, relative_path) do nothing""",
                [
                    (
                        manifest_hash,
                        row["namespace"],
                        row["relative_path"],
                        row["content"],
                        row["sha256"],
                        row["byte_size"],
                        published_by,
                    )
                    for row in rows
                ],
            )
        return len(rows) if result is None else len(rows)

    async def get_segment_ab_aggregate(self) -> list[dict[str, Any]]:
        # AVSIKTLIGT ingen _scoped(tenant_id) — den här funktionen har inget
        # tenant-sammanhang. select * from segment_ab_aggregate() kör som
        # funktionens SECURITY DEFINER-ägare (BYPASSRLS), inte som
        # snajp_app-sessionen, och returnerar bara aggregerade rader för
        # segment med >= 3 bidragande tenants (HAVING i själva funktionen).
        async with self.pool.acquire() as conn:
            records = await conn.fetch("select * from segment_ab_aggregate()")
        return [_row(r) for r in records]

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

    # -- Email-pipeline -------------------------------------------------------

    async def delete_emails_by_provider(self, tenant_id: str, provider: str) -> int:
        """Se Storage.delete_emails_by_provider.

        Bilagor, klassificeringar, utkast och beslutsloggens mailrader följer
        med via `on delete cascade` (migration 004). Ärendena (`ss_tickets`)
        gör det INTE — de refereras av mailet, inte tvärtom, och spåret av att
        ett ärende funnits ska inte försvinna för att en demoinkorg städas.
        """
        async with self._scoped(tenant_id) as conn:
            resultat = await conn.execute(
                "delete from ss_emails where tenant_id = $1 and provider = $2",
                tenant_id,
                provider,
            )
        # asyncpg returnerar kommandotaggen, t.ex. "DELETE 6".
        try:
            return int(str(resultat).rsplit(" ", 1)[-1])
        except ValueError:
            return 0

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
                where k.key_hash = $1 and k.active
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
        self, tenant_id: str, *, tenant_name: str, raw_key: str
    ) -> dict[str, Any]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_api_keys (tenant_id, tenant_name, key_prefix, key_hash)
                values ($1, $2, $3, $4)
                on conflict (key_hash) do update set active = true
                returning *
                """,
                tenant_id,
                tenant_name,
                raw_key[:12],
                key_hash,
            )
        return _row(record)

    async def list_outreach_messages(
        self, tenant_id: str, thread_id: str
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from outreach_messages
                where tenant_id = $1 and thread_id = $2
                order by id
                """,
                tenant_id,
                thread_id,
            )
        return [_row(r) for r in records]

    # -- Agentkonfiguration (autonomi + ICP, migration 023) -----------------

    async def get_agent_settings(self, tenant_id: str, *, agent_type: str) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            value = await conn.fetchval(
                "select settings from agent_configs where tenant_id = $1 and agent_type = $2",
                tenant_id,
                agent_type,
            )
        if value is None:
            return {}
        return json.loads(value) if isinstance(value, str) else dict(value)

    async def set_agent_settings(
        self, tenant_id: str, *, agent_type: str, settings: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            # Raden kan saknas helt: agent_configs skapas inte vid onboarding,
            # bara när någon faktiskt konfigurerar agenten. unique(tenant_id,
            # agent_type) finns sedan 010 och gör upserten säker.
            value = await conn.fetchval(
                """
                insert into agent_configs (tenant_id, agent_type, settings)
                values ($1, $2, $3::jsonb)
                on conflict (tenant_id, agent_type)
                do update set settings = excluded.settings, updated_at = now()
                returning settings
                """,
                tenant_id,
                agent_type,
                json.dumps(settings, ensure_ascii=False),
            )
        return json.loads(value) if isinstance(value, str) else dict(value)

    async def list_review_queue(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select q.*, m.subject, m.body, m.id as message_id,
                       p.contact_email as prospect_email, p.company_name
                from send_queue q
                join outreach_threads t on t.id = q.thread_id
                left join prospects p on p.id = t.prospect_id
                left join lateral (
                  -- order by id, inte created_at: outreach_messages HAR ingen
                  -- created_at (migration 010). Samma sortering som
                  -- get_pending_outreach_message redan använder.
                  select * from outreach_messages om
                  where om.thread_id = q.thread_id and om.sent_at is null
                  order by om.id limit 1
                ) m on true
                where q.tenant_id = $1 and q.status = 'awaiting_review'
                order by q.scheduled_at
                limit $2
                """,
                tenant_id,
                limit,
            )
        return [_row(r) for r in records]

    # -- Rate limiting ------------------------------------------------------

    async def count_rate_events(
        self, *, scope_kind: str, scope_id: str, kind: str, since: Any
    ) -> int:
        # Oskopad anslutning: tabellen har ingen tenant-kolumn, och ett av
        # scopen (ip) tillhör den anonyma demon som saknar tenant helt.
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                select count(*) from platform_rate_events
                where scope_kind = $1 and scope_id = $2 and kind = $3 and created_at >= $4
                """,
                scope_kind,
                scope_id,
                kind,
                since,
            )

    async def record_rate_events(
        self, *, scope_kind: str, scope_id: str, kind: str, count: int
    ) -> None:
        if count <= 0:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                insert into platform_rate_events (scope_kind, scope_id, kind)
                select $1, $2, $3 from generate_series(1, $4)
                """,
                scope_kind,
                scope_id,
                kind,
                count,
            )
            # Städning i samma anslutning. Fönstret är en timme; allt äldre än
            # ett dygn är avfall. Ser dyrt ut att köra varje gång, är det inte:
            # med platform_rate_events_created_idx hittar den noll rader på en
            # indexskanning i normalfallet. Det är billigare än pg_cron att
            # underhålla och kan inte glömmas bort vid en miljöflytt.
            await conn.execute(
                "delete from platform_rate_events where created_at < now() - interval '1 day'"
            )

    # -- Admin: cross-tenant-läsning (Fas 6) --------------------------------
    #
    # Oskopade anslutningar med flit: de här frågorna spänner över alla
    # tenants och kan inte köras under app.tenant_id. Skyddet ligger i
    # API-lagret (require_master_key) och i att metoderna bara anropas
    # därifrån — inte i RLS, som per definition inte kan uttrycka
    # "alla tenants".

    async def list_tenants_with_stats(self) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                select t.id, t.slug, t.name, t.active, t.created_at,
                       coalesce(k.tickets, 0)      as tickets,
                       coalesce(r.runs, 0)         as runs,
                       coalesce(r.tokens_in, 0)    as tokens_in,
                       coalesce(r.tokens_out, 0)   as tokens_out,
                       coalesce(e.errors, 0)       as errors,
                       r.last_activity
                from ss_tenants t
                left join lateral (
                  select count(*) as tickets from ss_tickets where tenant_id = t.id
                ) k on true
                left join lateral (
                  select count(*) as runs,
                         sum(tokens_in) as tokens_in,
                         sum(tokens_out) as tokens_out,
                         max(created_at) as last_activity
                  from agent_runs where tenant_id = t.id
                ) r on true
                left join lateral (
                  select count(*) as errors from platform_events
                  where tenant_id = t.id and level = 'error'
                ) e on true
                order by r.last_activity desc nulls last, t.created_at
                """
            )
        return [_row(r) for r in records]

    async def list_agent_runs_all(
        self,
        *,
        tenant_id: str | None = None,
        agent_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                select r.*, t.slug as tenant_slug, t.name as tenant_name
                from agent_runs r
                join ss_tenants t on t.id = r.tenant_id
                where ($1::uuid is null or r.tenant_id = $1)
                  and ($2::text is null or r.agent_type = $2)
                order by r.created_at desc
                limit $3
                """,
                tenant_id,
                agent_type,
                limit,
            )
        return [_avkoda_jsonb(_row(r), "step_log", "grounding") for r in records]

    async def get_agent_run(self, run_id: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                select r.*, t.slug as tenant_slug, t.name as tenant_name
                from agent_runs r join ss_tenants t on t.id = r.tenant_id
                where r.id = $1
                """,
                run_id,
            )
        return _avkoda_jsonb(_row(record), "step_log", "grounding")

    async def list_platform_events(
        self,
        *,
        level: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                select e.*, t.slug as tenant_slug
                from platform_events e
                left join ss_tenants t on t.id = e.tenant_id
                where ($1::text is null or e.level = $1)
                  and ($2::uuid is null or e.tenant_id = $2)
                order by e.created_at desc
                limit $3
                """,
                level,
                tenant_id,
                limit,
            )
        return [_avkoda_jsonb(_row(r), "detail") for r in records]

    async def log_platform_event(
        self,
        *,
        level: str,
        source: str,
        message: str,
        tenant_id: str | None = None,
        run_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                insert into platform_events (tenant_id, level, source, message, detail, run_id)
                values ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                tenant_id,
                level,
                source,
                message,
                json.dumps(detail or {}, ensure_ascii=False),
                run_id,
            )

    async def close(self) -> None:
        await self.pool.close()
