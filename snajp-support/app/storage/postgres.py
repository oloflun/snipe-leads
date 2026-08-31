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
import logging
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any

import asyncpg

from .base import (
    ANALYTICS_COVERAGE,
    KUNDDATA_FALT,
    bk_belopp,
    bk_datum,
    kontrollera_bk_balans,
    kontrollera_bk_riktning,
    kontrollera_bk_status,
    normalisera_kunddata,
    status_transition_allowed,
)

logger = logging.getLogger("snajp-support.storage")

#: Prospektets profilfält (migration 031). ALLOWLIST, inte en genomsläpp:
#: kolumnnamnen sätts in i SQL-satsen som text, och det enda som gör det säkert
#: är att de aldrig kan komma från anroparen. Värdena går som parametrar.
_PROSPEKT_PROFILFALT = frozenset(
    {"orgnr", "ort", "postnr", "sni", "website", "anstallda", "omsattning"}
)


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


#: RRF-konstanten. 60 är standarden (Elasticsearch, OpenSearch, Qdrant) och
#: fungerar utan korpus-specifik tuning — poängen 1/(k+rang) gör att en
#: förstaplats väger tungt utan att ensam dominera en artikel som rankar
#: hyggligt i BÅDA listorna.
_RRF_K = 60


def _rrf_fusion(
    vektor: list[dict[str, Any]], fulltext: list[dict[str, Any]], *, limit: int
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion över två rankade träfflistor.

    Ren funktion med flit — sammanslagningen är det enda i hybridssökningen
    som går att falsifiera utan databas, och då ska den ligga där ett test
    når den. Poäng per dokument: summan av 1/(k + rang) i varje lista där
    det förekommer. Dokumentets FÄLT tas från den lista som rankade det
    först (vektorns similarity är den mer informativa siffran när båda
    hittade samma artikel).
    """
    poang: dict[str, float] = {}
    rader: dict[str, dict[str, Any]] = {}
    for lista in (vektor, fulltext):
        for rang, rad in enumerate(lista):
            nyckel = str(rad["id"])
            poang[nyckel] = poang.get(nyckel, 0.0) + 1.0 / (_RRF_K + rang + 1)
            rader.setdefault(nyckel, rad)
    ordnade = sorted(poang, key=lambda n: poang[n], reverse=True)
    return [rader[n] for n in ordnade[:limit]]


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


def _avkoda_prospekt(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Prospektets enda jsonb-kolumn, avkodad EN gång för alla fyra läsvägar.

    `score_breakdown` är den enda jsonb-kolumnen på `prospects` (migration 031),
    och den nådde frontenden som en sträng. Följden var att /dashboard/leads,
    /admin/leads och /admin/contacts kraschade i webbläsaren med

        e.score_breakdown?.find is not a function

    och sidan ersattes av webbläsarens egen felruta — alltså inget serverfel,
    ingenting i loggen, och statuskoden 200 hela vägen.

    Det är SAMMA fel som docstringen ovanför redan beskriver för `step_log`,
    och det uppstod igen av samma två skäl: avkodningen bor per anropsställe,
    och sviten kör mot MemoryStorage, som lämnar riktiga listor. En kolumn som
    läggs till senare (031 kom långt efter de här funktionerna) ärver alltså
    ingenting och testas inte.

    Egen funktion och inte fyra `_avkoda_jsonb(...)`-anrop: nästa jsonb-kolumn
    på prospects ska behöva läggas till på ETT ställe, inte fyra. Fyra platser
    som måste ändras tillsammans är hur den här buggen såg ut från början.
    """
    return _avkoda_jsonb(data, "score_breakdown")


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
                -- conversation_id kommer ur joinen, INTE ur ss_tickets:
                -- kolumnen finns inte där (se 002_snajp_support.sql), den
                -- sitter på ss_conversations.ticket_id, som är unique — ett
                -- ärende har högst ett samtal.
                --
                -- Utan joinen saknade ticket-dicten fältet helt, medan
                -- MemoryStorage sätter det (memory.py). Följden var att
                -- arbetsminne.alla_samtalsrader kastade KeyError mot Postgres
                -- men aldrig i sviten, och kraschen kom EFTER att svaret
                -- redan tagits fram — LLM-anropet betalt, svaret bortkastat,
                -- kunden fick "Svaret gick inte att ta fram".
                --
                -- LEFT join, inte inner: ett ärende utan samtal ska ligga kvar
                -- i historiken med conversation_id = NULL, inte försvinna ur
                -- den. Läsaren måste tåla NULL.
                select t.*, c.id as conversation_id
                from ss_tickets t
                left join ss_conversations c
                  on c.ticket_id = t.id and c.tenant_id = t.tenant_id
                where t.tenant_id = $1 and t.customer_id = $2
                order by t.created_at desc, t.id desc limit 20
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
        is_test: bool = False,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            ticket = await conn.fetchrow(
                """
                insert into ss_tickets (tenant_id, customer_id, subject, category, channel, priority, is_test)
                values ($1, $2, $3, $4, $5, $6, $7) returning *
                """,
                tenant_id,
                customer_id,
                subject,
                category,
                channel,
                priority,
                is_test,
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
        is_test: bool | None = None,
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
                  is_test = case when $7::boolean is null then is_test else $7 end,
                  updated_at = now()
                where tenant_id = $1 and id = $2 returning *
                """,
                tenant_id,
                ticket_id,
                new_status,
                category,
                priority,
                escalation_reason,
                is_test,
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

    #: Under den här likheten räknas en vektorträff som brus. Tröskeln är
    #: konservativ med flit — en artikel som inte handlar om frågan är sämre
    #: underlag än ingen artikel alls, eftersom modellen grundar sig i den.
    VEKTOR_MIN_LIKHET = 0.25

    async def search_kb(
        self,
        tenant_id: str,
        query: str,
        embedding: list[float] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Vektorsökning när det finns en vektor, ANNARS OCH DESSUTOM fulltext.

        Fallbacken är inte kosmetik. Vektorvägen filtrerar på
        `embedding is not null`, och noll av kundernas artiklar bar en vektor
        under hela den period Gemini-API:t svarade 403 (se agent/embeddings.py).
        En kund som seedat sin bas EFTER att embeddings började fungera har
        alltså vektorer på de nya artiklarna och inga på de gamla — och den
        gamla koden returnerade då tom lista så fort de nyaste tre låg under
        likhetströskeln, trots att svaret stod i en äldre artikel.

        Tom träfflista är dessutom ett HÅRT eskaleringsvillkor i
        agent/support_agent.py. En retrievalmiss blir därför inte ett sämre
        svar utan ett ärende hos en människa, vilket är exakt det fel som
        rapporterades som "eskalerar trots att underlag finns".
        """
        async with self._scoped(tenant_id) as conn:
            # HYBRID, inte antingen/eller (2026-08-26). Kedjan föll förut
            # bara tillbaka när vektorlistan var HELT tom — en enda svag
            # vektorträff över tröskeln räckte för att fulltexten aldrig
            # tillfrågades, även när svaret stod i en artikel fulltexten
            # hade hittat direkt.
            #
            # Sammanslagningen är Reciprocal Rank Fusion (k=60) — standarden i
            # Elasticsearch/OpenSearch/Qdrant, vald för att den viktar RANG i
            # stället för poäng: cosinuslikhet och ts_rank lever på olika
            # skalor och går inte att jämföra direkt, men "artikeln båda
            # vägarna rankar högt" är en robust signal oavsett skala.
            # Referensmätningar (digitalapplied 2026, ParadeDB) visar
            # recall@10 65-78 % för en väg ensam mot ~91 % för RRF-hybrid.
            vektor: list[dict[str, Any]] = []
            if embedding is not None:
                # Fler kandidater än limit in i fusionen: RRF:s poäng bygger
                # på rang i BÅDA listorna, och en lista kapad till limit har
                # redan kastat de dokument fusionen skulle ha lyft.
                vektor = await self._sok_vektor(conn, tenant_id, embedding, limit * 3)
            fulltext = await self._sok_fulltext(conn, tenant_id, query, limit * 3)
        return _rrf_fusion(vektor, fulltext, limit=limit)

    async def _sok_vektor(
        self, conn, tenant_id: str, embedding: list[float], limit: int
    ) -> list[dict[str, Any]]:
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
            if float(r["similarity"]) >= self.VEKTOR_MIN_LIKHET
        ]

    async def _sok_fulltext(
        self, conn, tenant_id: str, query: str, limit: int
    ) -> list[dict[str, Any]]:
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
            # workspace_id hämtas ur kopplingen NÄR DEN FINNS, annars NULL.
            #
            # Här stod tidigare en `insert ... select ... from workspaces
            # where ss_tenant_id = $1`, och kommentaren påstod att en saknad
            # workspace vore "ett riktigt fel". Det var värre än så: en select
            # utan träffar infogar noll rader. Ingen krasch, inget
            # felmeddelande, ingen avregistrering — exakt det utfall
            # kommentaren sa att den ville undvika.
            #
            # Upptäckt 2026-08-24 när avregistreringskedjan provkördes skarpt:
            # två tenants i development saknar arbetsyta. Kolumnen är nullbar
            # sedan migration 049, och `send_guard` regel 3 läser ändå via
            # tenant_id — skyddet gäller alltså oavsett workspace_id.
            await conn.execute(
                """
                insert into suppressions (workspace_id, tenant_id, email, reason)
                values (
                    (select w.id from workspaces w where w.ss_tenant_id = $1 limit 1),
                    $1, $2, $3
                )
                on conflict do nothing
                """,
                tenant_id,
                adress,
                reason,
            )

    async def avregistreringstoken(self, tenant_id: str, *, email: str) -> str:
        adress = str(email or "").strip().casefold()
        if not adress:
            raise ValueError("avregistreringstoken kräver en e-postadress.")
        from ..leads.utskicksfot import ny_token

        async with self._scoped(tenant_id) as conn:
            # `do update` och inte `do nothing`: en `do nothing`-konflikt
            # returnerar INGEN rad, och då hade anroparen fått None för en
            # adress som redan har en giltig länk. Uppdateringen är en no-op
            # på värdet men tvingar fram returraden.
            return await conn.fetchval(
                """
                insert into ss_avregistreringslankar (token, tenant_id, email)
                values ($1, $2, $3)
                on conflict (tenant_id, lower(email))
                do update set email = excluded.email
                returning token
                """,
                ny_token(),
                tenant_id,
                adress,
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

    async def find_outreach_thread(
        self, tenant_id: str, *, prospect_id: str
    ) -> dict[str, Any] | None:
        # Samma fråga som läsdelen i ensure_outreach_thread nedan — men utan
        # skapandet. Se base.py för varför en GET aldrig får lämna spår.
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                select * from outreach_threads
                where tenant_id = $1 and prospect_id = $2
                order by created_at limit 1
                """,
                tenant_id,
                prospect_id,
            )
        return _row(record) if record else None

    async def ensure_outreach_thread(
        self, tenant_id: str, *, prospect_id: str
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                select * from outreach_threads
                where tenant_id = $1 and prospect_id = $2
                order by created_at limit 1
                """,
                tenant_id,
                prospect_id,
            )
            if record is None:
                record = await conn.fetchrow(
                    """
                    insert into outreach_threads (tenant_id, prospect_id)
                    values ($1, $2)
                    returning *
                    """,
                    tenant_id,
                    prospect_id,
                )
        return _row(record)

    async def record_inbound_reply(
        self, tenant_id: str, *, thread_id: str, body: str
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            message = await conn.fetchrow(
                """
                insert into outreach_messages
                  (tenant_id, thread_id, direction, body, sent_at)
                values ($1, $2, 'inbound', $3, now())
                returning *
                """,
                tenant_id,
                thread_id,
                body,
            )
            await conn.execute(
                "update outreach_threads set last_inbound_at = now() where tenant_id = $1 and id = $2",
                tenant_id,
                thread_id,
            )
        return _row(message)

    async def list_outreach_threads(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select t.*,
                       p.company_name,
                       p.contact_email,
                       count(m.id) filter (
                         where m.direction = 'outbound' and m.sent_at is not null
                       ) as outbound_sent_count,
                       max(m.sent_at) filter (
                         where m.direction = 'outbound'
                       ) as last_outbound_sent_at,
                       (count(m.id) filter (
                          where m.direction = 'outbound' and m.sent_at is null
                        ) > 0
                        or count(q.id) filter (
                          where q.status in ('queued', 'awaiting_review')
                        ) > 0) as has_pending_item
                from outreach_threads t
                left join prospects p on p.id = t.prospect_id
                left join outreach_messages m on m.thread_id = t.id
                left join send_queue q on q.thread_id = t.id
                where t.tenant_id = $1
                group by t.id, p.company_name, p.contact_email
                """,
                tenant_id,
            )
        return [_row(r) for r in records]

    async def cancel_pending_sends(self, tenant_id: str, thread_id: str) -> int:
        async with self._scoped(tenant_id) as conn:
            resultat = await conn.execute(
                """
                update send_queue set status = 'cancelled'
                where tenant_id = $1 and thread_id = $2
                  and status in ('queued', 'awaiting_review')
                """,
                tenant_id,
                thread_id,
            )
        return int(resultat.split()[-1])

    async def reschedule_pending_sends(
        self, tenant_id: str, thread_id: str, *, until
    ) -> int:
        async with self._scoped(tenant_id) as conn:
            resultat = await conn.execute(
                """
                update send_queue set scheduled_at = $3
                where tenant_id = $1 and thread_id = $2 and status = 'queued'
                """,
                tenant_id,
                thread_id,
                until,
            )
        return int(resultat.split()[-1])

    # -- Agentens föreslagna lärdomar (migration 051) -----------------------

    async def save_agent_suggestion(
        self,
        tenant_id: str,
        *,
        agent_type: str,
        kind: str,
        title: str,
        content: dict[str, Any],
        dedupe_key: str,
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            # `on conflict do nothing` mot det partiella unika indexet — en
            # dubblett ger None till anroparen i stället för en ny rad, samma
            # kontrakt som MemoryStorage.
            record = await conn.fetchrow(
                """
                insert into agent_suggestions
                  (tenant_id, agent_type, kind, title, content, dedupe_key)
                values ($1, $2, $3, $4, $5, $6)
                on conflict (tenant_id, dedupe_key) where status = 'ny'
                do nothing
                returning *
                """,
                tenant_id,
                agent_type,
                kind,
                title,
                json.dumps(content, ensure_ascii=False),
                dedupe_key,
            )
        return _row(record)

    async def list_agent_suggestions(
        self, tenant_id: str, *, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from agent_suggestions
                where tenant_id = $1 and ($2::text is null or status = $2)
                order by created_at desc
                limit $3
                """,
                tenant_id,
                status,
                limit,
            )
        return [_row(r) for r in records]

    async def update_agent_suggestion_status(
        self, tenant_id: str, suggestion_id: str, *, status: str
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                update agent_suggestions set status = $3
                where tenant_id = $1 and id = $2
                returning *
                """,
                tenant_id,
                suggestion_id,
                status,
            )
        return _row(record)

    # -- Kundens dom över en körning (agent_feedback, migration 010) --------

    async def save_agent_feedback(
        self,
        tenant_id: str,
        *,
        run_id: str,
        verdict: str,
        comment: str | None = None,
        corrected_output: str | None = None,
    ) -> dict[str, Any]:
        # Kolumncheck och FK kastar i Postgres av sig själva; run-ägarskapet
        # kontrolleras explicit så att ett run_id från EN ANNAN tenant ger
        # samma fel som ett som inte finns — FK:n ensam skiljer inte på dem.
        async with self._scoped(tenant_id) as conn:
            ags = await conn.fetchval(
                "select 1 from agent_runs where tenant_id = $1 and id = $2",
                tenant_id,
                run_id,
            )
            if not ags:
                raise ValueError(f"run_id={run_id!r} finns inte i agent_runs hos tenanten.")
            record = await conn.fetchrow(
                """
                insert into agent_feedback
                  (tenant_id, run_id, verdict, comment, corrected_output)
                values ($1, $2, $3, $4, $5)
                returning *
                """,
                tenant_id,
                run_id,
                verdict,
                comment,
                corrected_output,
            )
        return _row(record)

    async def list_agent_feedback(
        self, tenant_id: str, *, verdict: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from agent_feedback
                where tenant_id = $1 and ($2::text is null or verdict = $2)
                order by created_at desc
                limit $3
                """,
                tenant_id,
                verdict,
                limit,
            )
        return [_row(r) for r in records]

    # -- Kundminne (migration 052) ------------------------------------------

    async def add_customer_facts(
        self, tenant_id: str, customer_id: str, *, fakta: list[str]
    ) -> int:
        rensade = [str(r or "").strip() for r in fakta]
        rensade = [r for r in rensade if r]
        if not rensade:
            return 0
        antal = 0
        async with self._scoped(tenant_id) as conn:
            for text in rensade:
                # Dubblettspärr per (kund, fakta) — exakt samma rad två gånger
                # är ett dubbelklick, inte ny kunskap. Ingen unik constraint i
                # schemat (fakta är fritext utan normaliserad form), så
                # kontrollen görs här, i samma transaktionsscope.
                finns = await conn.fetchval(
                    """
                    select 1 from customer_memory
                    where tenant_id = $1 and customer_id = $2
                      and lower(fakta) = lower($3)
                    """,
                    tenant_id,
                    customer_id,
                    text,
                )
                if finns:
                    continue
                await conn.execute(
                    """
                    insert into customer_memory (tenant_id, customer_id, fakta)
                    values ($1, $2, $3)
                    """,
                    tenant_id,
                    customer_id,
                    text,
                )
                antal += 1
        return antal

    async def get_customer_facts(
        self, tenant_id: str, customer_id: str, *, limit: int = 12
    ) -> list[str]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select fakta from (
                  select fakta, created_at from customer_memory
                  where tenant_id = $1 and customer_id = $2
                  order by created_at desc
                  limit $3
                ) senaste
                order by created_at asc
                """,
                tenant_id,
                customer_id,
                max(1, limit),
            )
        return [str(r["fakta"]) for r in records]

    # -- Golden eval-cases (agent_evals) ------------------------------------

    async def save_eval_case(
        self,
        tenant_id: str,
        *,
        agent_type: str,
        input_text: str,
        expected_traits: dict[str, Any],
        approved_output: str | None = None,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into agent_evals
                  (tenant_id, agent_type, input, expected_traits, approved_output)
                values ($1, $2, $3, $4, $5)
                returning *
                """,
                tenant_id,
                agent_type,
                input_text,
                json.dumps(expected_traits, ensure_ascii=False),
                approved_output,
            )
        rad = _row(record)
        rad["expected_traits"] = expected_traits
        return rad

    async def list_eval_cases(
        self, tenant_id: str, *, agent_type: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from agent_evals
                where tenant_id = $1 and ($2::text is null or agent_type = $2)
                order by created_at
                limit $3
                """,
                tenant_id,
                agent_type,
                limit,
            )
        rader = []
        for r in records:
            rad = _row(r)
            try:
                rad["expected_traits"] = json.loads(rad.get("expected_traits") or "{}")
            except (TypeError, ValueError):
                rad["expected_traits"] = {}
            rader.append(rad)
        return rader

    async def create_prospect(
        self,
        tenant_id: str,
        *,
        company_name: str,
        contact_name: str | None = None,
        contact_email: str | None = None,
        origin: str = "manual",
        profil: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Profilfälten (migration 031) sätts i SAMMA insert och inte med en
        # efterföljande update. En prospektrad som existerar utan sin ort och
        # sitt org.nr, om än bara i en millisekund, är en rad granskningsvyn kan
        # hinna läsa — och `update_prospect` tar med flit bara bedömningsfälten.
        extra = {
            namn: värde
            for namn, värde in (profil or {}).items()
            if namn in _PROSPEKT_PROFILFALT and värde is not None
        }
        kolumner = ", ".join(extra)
        platshallare = ", ".join(f"${i}" for i in range(6, 6 + len(extra)))

        async with self._scoped(tenant_id) as conn:
            try:
                record = await conn.fetchrow(
                    f"""
                    insert into prospects
                      (tenant_id, company_name, contact_name, contact_email, origin
                       {", " + kolumner if extra else ""})
                    values ($1, $2, $3, $4, $5{", " + platshallare if extra else ""})
                    returning *
                    """,
                    tenant_id,
                    company_name,
                    contact_name,
                    contact_email,
                    origin,
                    *extra.values(),
                )
            except asyncpg.UndefinedColumnError:
                # Migration 039 är inte körd i den här databasen ännu.
                #
                # Koden deployas från grenen, migrationerna körs av en människa
                # med databaslösenordet — de två landar alltså inte samtidigt.
                # Utan den här grenen slutar VARJE prospekt att gå att skapa
                # under mellantiden, inklusive de som inte har med exempelbolag
                # att göra: en ny kolumn hade tagit ner den befintliga
                # pipelinen.
                #
                # Exempelbolag kan däremot inte skapas säkert utan kolumnen —
                # utan `origin` finns ingen markering, och utan markering kan
                # send-guarden inte skilja dem från riktiga prospekt.
                if origin != "manual":
                    raise RuntimeError(
                        "Kolumnen prospects.origin saknas (migration 039 är inte körd). "
                        "Exempelbolag kan inte skapas utan den — de skulle inte gå att "
                        "skilja från riktiga prospekt i utskicksspärren."
                    ) from None
                logger.warning(
                    "prospects.origin saknas — migration 039 är inte körd. "
                    "Skapar prospektet utan ursprungsmarkering."
                )
                record = await conn.fetchrow(
                    """
                    insert into prospects (tenant_id, company_name, contact_name, contact_email)
                    values ($1, $2, $3, $4) returning *
                    """,
                    tenant_id,
                    company_name,
                    contact_name,
                    contact_email,
                )
        return _avkoda_prospekt(_row(record))

    async def get_prospect(self, tenant_id: str, prospect_id: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                "select * from prospects where tenant_id = $1 and id = $2", tenant_id, prospect_id
            )
        return _avkoda_prospekt(_row(record))

    async def list_prospects(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                "select * from prospects where tenant_id = $1 order by created_at desc limit $2",
                tenant_id,
                limit,
            )
        return [_avkoda_prospekt(_row(r)) for r in records]

    async def update_prospect(
        self,
        tenant_id: str,
        prospect_id: str,
        *,
        status: str | None = None,
        icp_fit: float | None = None,
        qualified: bool | None = None,
        disqualifiers: list[str] | None = None,
        origin: str | None = None,
        orgnr: str | None = None,
        website: str | None = None,
        contact_email: str | None = None,
    ) -> dict[str, Any] | None:
        # Dynamisk SET-lista: en PATCH ska kunna sätta ETT fält utan att nolla
        # de andra, och en fast update-sats hade krävt att anroparen skickar
        # allt varje gång — vilket är hur en bedömning råkar skrivas över.
        updates = {
            "status": status,
            "icp_fit": icp_fit,
            "qualified": qualified,
            "disqualifiers": disqualifiers,
            "origin": origin,
            "orgnr": orgnr,
            "website": website,
            "contact_email": contact_email,
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
        return _avkoda_prospekt(_row(record))

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
        # Migration 055. Se base.py:s docstring för värdemängden.
        model: str | None = None,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into agent_runs
                  (tenant_id, agent_type, pack_version, skills_used, input, output,
                   step_log, tokens_in, tokens_out, latency_ms, is_test, model)
                values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
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
                model,
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
        # Samma avkodning som list_agent_runs_all och get_agent_run redan gör.
        # Saknades här, och det syntes inte på ett halvår av EN anledning: den
        # enda konsumenten — översiktens körningsräknare — frågade efter
        # `agent_type=leads`, en sträng ingen kodväg skriver, och fick alltid
        # noll rader. Så fort filtret rättades kom raderna fram, och adminytans
        # arbetsyta föll på `step_log.filter is not a function`.
        #
        # Två fel som gömde varandra: det ena gjorde det andra osynligt.
        return [_avkoda_jsonb(_row(r), "step_log", "grounding") for r in records]

    async def weekly_analytics(self, tenant_id: str, *, weeks: int = 8) -> dict[str, Any]:
        # Se protokollet i base.py för varför `coverage` finns.
        #
        # Veckorna genereras ur en serie och inte ur raderna. Skillnaden är inte
        # kosmetisk: grupperar man bara det som finns FÖRSVINNER en tyst vecka
        # ur tabellen, och en kurva utan hål ser ut som att inget hände fastän
        # den i själva verket saknar sin sämsta vecka. Här blir en vecka utan
        # trafik en rad med nollor, vilket är ett mätvärde — till skillnad från
        # ett mätvärde vi inte samlar in alls, som blir `coverage: false`.
        #
        # `is_test` räknas bort: adminytans provkörningar är våra, inte kundens
        # (migration 036).
        weeks = max(1, min(weeks, 52))

        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                with veckor as (
                  select generate_series(
                    date_trunc('week', now()) - make_interval(weeks => $2::int - 1),
                    date_trunc('week', now()),
                    interval '1 week'
                  ) as vecka
                ),
                utskick as (
                  select date_trunc('week', m.sent_at) as vecka,
                         count(*) filter (where m.direction = 'outbound') as skick,
                         count(*) filter (where m.direction = 'inbound')  as svar
                    from outreach_messages m
                   where m.tenant_id = $1 and m.sent_at is not null
                   group by 1
                ),
                korningar as (
                  select date_trunc('week', r.created_at) as vecka,
                         count(*) filter (where r.agent_type like 'leads%')     as leads_runs,
                         count(*) filter (where r.agent_type = 'support')       as support_runs
                    from agent_runs r
                   where r.tenant_id = $1 and not r.is_test
                   group by 1
                ),
                arenden as (
                  select date_trunc('week', t.created_at) as vecka,
                         count(*)                                              as arenden,
                         count(*) filter (where t.status = 'escalated')         as eskalerade,
                         count(*) filter (where t.status in ('resolved','closed')) as avslutade
                    from ss_tickets t
                   where t.tenant_id = $1
                   group by 1
                )
                select v.vecka,
                       coalesce(u.skick, 0)         as skick,
                       coalesce(u.svar, 0)          as svar,
                       coalesce(k.leads_runs, 0)    as leads_runs,
                       coalesce(k.support_runs, 0)  as support_runs,
                       coalesce(a.arenden, 0)       as arenden,
                       coalesce(a.eskalerade, 0)    as eskalerade,
                       coalesce(a.avslutade, 0)     as avslutade
                  from veckor v
                  left join utskick   u on u.vecka = v.vecka
                  left join korningar k on k.vecka = v.vecka
                  left join arenden   a on a.vecka = v.vecka
                 order by v.vecka
                """,
                tenant_id,
                weeks,
            )

        return {
            "weeks": [
                {
                    "week": f"v{r['vecka'].isocalendar().week}",
                    "start": r["vecka"].isoformat(),
                    "sent": r["skick"],
                    "replies": r["svar"],
                    "leads_runs": r["leads_runs"],
                    "support_runs": r["support_runs"],
                    "tickets": r["arenden"],
                    "escalated": r["eskalerade"],
                    "resolved": r["avslutade"],
                }
                for r in records
            ],
            "coverage": ANALYTICS_COVERAGE,
        }

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
        is_test: bool = False,
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into ss_emails
                  (tenant_id, provider, provider_message_id, from_email, from_name,
                   subject, body_text, received_at, is_test)
                values ($1, $2, $3, $4, $5, $6, $7, coalesce($8::timestamptz, now()), $9)
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
                is_test,
            )
        return _row(record)

    async def delete_mock_emails(self, tenant_id: str, *, category: str | None = None) -> int:
        """Se Storage.delete_mock_emails.

        Bilagor, klassificeringar, utkast och beslutsloggens mailrader följer
        med via `on delete cascade` (migration 004). Ärendena (`ss_tickets`)
        gör det INTE — de refereras av mailet, inte tvärtom, och spåret av att
        ett ärende funnits ska inte försvinna för att en demoinkorg städas.
        """
        async with self._scoped(tenant_id) as conn:
            resultat = await conn.execute(
                """
                delete from ss_emails e
                 where e.tenant_id = $1
                   and e.provider = 'mock'
                   and ($2::text is null or exists(
                         select 1 from ss_classifications c
                          where c.email_id = e.id and c.category = $2))
                """,
                tenant_id,
                category,
            )
        try:
            return int(str(resultat).rsplit(" ", 1)[-1])
        except ValueError:
            return 0

    async def list_emails(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
        is_test: bool | None = False,
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
                  and ($6::boolean is null or e.is_test = $6)
                order by e.received_at desc
                limit $5
                """,
                tenant_id,
                status,
                category,
                search,
                limit,
                is_test,
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
        rows = await self.list_emails(tenant_id, limit=1000, is_test=None)
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
        is_test: bool | None = None,
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                update ss_emails set
                  status = coalesce($3, status),
                  ticket_id = coalesce($4::uuid, ticket_id),
                  is_test = case when $5::boolean is null then is_test else $5 end,
                  updated_at = now()
                where tenant_id = $1 and id = $2 returning *
                """,
                tenant_id,
                email_id,
                status,
                ticket_id,
                is_test,
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

    async def list_replies(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select m.id, m.body, m.sent_at, m.thread_id,
                       p.company_name, p.contact_name, p.contact_email, p.status
                  from outreach_messages m
                  join outreach_threads t on t.id = m.thread_id and t.tenant_id = m.tenant_id
                  join prospects p on p.id = t.prospect_id and p.tenant_id = m.tenant_id
                 where m.tenant_id = $1
                   and m.direction = 'inbound'
                 order by m.sent_at desc nulls last
                 limit $2
                """,
                tenant_id,
                limit,
            )
        return [_row(r) for r in records]

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

    # -- Instruktionslagret (migration 049) ---------------------------------

    async def get_global_instructions(self) -> dict[str, Any] | None:
        # Ingen tenant-scoping: tabellen är plattformens och har ingen
        # tenant_id. Vägen hit går bara via master-nyckeln (api/deps.py).
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "select * from agent_global_instructions where aktiv"
            )
        return _row(record)

    async def save_global_instructions(
        self,
        *,
        ravtext: str,
        strukturerad_md: str,
        kalla: str = "ai",
        uppdaterad_av: str | None = None,
    ) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            # EN transaktion. Det partiella unika indexet tillåter exakt en
            # aktiv rad, så avaktivering och insert måste lyckas ihop — annars
            # kan ett avbrott mellan dem lämna noll aktiva rader, och agenten
            # faller tyst tillbaka på filen som om ingen instruktion fanns.
            async with conn.transaction():
                await conn.execute(
                    "update agent_global_instructions set aktiv = false where aktiv"
                )
                record = await conn.fetchrow(
                    """
                    insert into agent_global_instructions
                        (ravtext, strukturerad_md, kalla, uppdaterad_av, aktiv)
                    values ($1, $2, $3, $4, true)
                    returning *
                    """,
                    ravtext,
                    strukturerad_md,
                    kalla,
                    uppdaterad_av,
                )
        return _row(record)

    async def list_global_instructions(self, *, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                select id, kalla, aktiv, uppdaterad_av, created_at,
                       length(ravtext) as ravtext_tecken,
                       length(strukturerad_md) as strukturerad_tecken
                from agent_global_instructions
                order by created_at desc
                limit $1
                """,
                limit,
            )
        return [_row(r) for r in records]

    async def get_agent_config(self, tenant_id: str, *, agent_type: str) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                select instructions_md, instructions_rav, tone, taxonomy,
                       language_policy, status, pinned_pack_version
                from agent_configs where tenant_id = $1 and agent_type = $2
                """,
                tenant_id,
                agent_type,
            )
        # En saknad rad är inte ett fel: agent_configs skapas först när någon
        # konfigurerar agenten. Tomma strängar betyder "inget lager", vilket är
        # exakt vad läsvägen ska göra av det.
        return _row(record) or {
            "instructions_md": "",
            "instructions_rav": "",
            "tone": "",
            "taxonomy": [],
            "language_policy": "sv_default",
            "status": "draft",
            "pinned_pack_version": None,
        }

    async def set_agent_instructions(
        self,
        tenant_id: str,
        *,
        agent_type: str,
        instructions_md: str,
        instructions_rav: str = "",
        tone: str | None = None,
    ) -> dict[str, Any]:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into agent_configs
                    (tenant_id, agent_type, instructions_md, instructions_rav, tone)
                values ($1, $2, $3, $4, coalesce($5, ''))
                on conflict (tenant_id, agent_type) do update set
                    instructions_md = excluded.instructions_md,
                    instructions_rav = excluded.instructions_rav,
                    -- coalesce på $5 och inte på excluded.tone: null betyder
                    -- "rör inte tonen", tom sträng betyder "nollställ den".
                    -- Utan skillnaden kan ett sparande av instruktioner inte
                    -- undvika att också skriva över tonen.
                    tone = coalesce($5, agent_configs.tone),
                    updated_at = now()
                returning instructions_md, instructions_rav, tone, taxonomy,
                          language_policy, status, pinned_pack_version
                """,
                tenant_id,
                agent_type,
                instructions_md,
                instructions_rav,
                tone,
            )
        return _row(record)

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
                       coalesce(k.escalated, 0)    as escalated,
                       coalesce(r.runs, 0)         as runs,
                       coalesce(r.test_runs, 0)    as test_runs,
                       coalesce(r.tokens_in, 0)    as tokens_in,
                       coalesce(r.tokens_out, 0)   as tokens_out,
                       coalesce(e.errors, 0)       as errors,
                       r.last_activity,
                       -- Kundregistret (053): registrets datum vinner, annars
                       -- tenantens skapelsedatum. Avtalet är null tills någon
                       -- registrerat ett — null ÄR "inget avtal".
                       coalesce(d.kund_sedan, t.created_at::date) as kund_sedan,
                       d.avtal_signerat
                from ss_tenants t
                left join ss_customer_details d on d.tenant_id = t.id
                left join lateral (
                  -- `escalated` bär fliken Fel & eskaleringar. Samma
                  -- statusvillkor som veckoanalysen (get_weekly_analytics).
                  select count(*) as tickets,
                         count(*) filter (where status = 'escalated') as escalated
                  from ss_tickets where tenant_id = t.id
                ) k on true
                left join lateral (
                  -- `runs` är KUNDVOLYM och räknar inte våra egna provkörningar.
                  -- Kolumnen finns sedan migration 036 men var alltid false
                  -- eftersom ingen anropsplats satte den; nu när den fylls i
                  -- kan siffran betyda det den påstår.
                  --
                  -- Tokens räknar däremot ALLA körningar. En provkörning kostar
                  -- lika mycket som en riktig, och en kostnadssiffra som döljer
                  -- vår egen förbrukning är en kostnadssiffra man planerar fel
                  -- efter.
                  select count(*) filter (where not is_test) as runs,
                         count(*) filter (where is_test) as test_runs,
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

    # -- Kundregister (migration 053) ---------------------------------------
    #
    # Oskopade anslutningar av samma skäl som adminläsningarna ovan: RLS-
    # policyn i 053 släpper bara fram snajp_app när INGEN tenant-kontext är
    # satt, och den enda anropsplatsen är admin_kunddata.py bakom
    # require_master_key.

    async def get_customer_details(self, tenant_id: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "select * from ss_customer_details where tenant_id = $1", tenant_id
            )
        return _row(record) if record else None

    async def orgnr_for_tenant(self, tenant_id: str) -> str | None:
        """Se base.Storage.orgnr_for_tenant — går via security definer-funktionen
        eftersom ss_customer_details RLS stänger ute tenant-skopade anrop."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval("select public.orgnr_for_current_tenant()")

    async def upsert_customer_details(
        self, tenant_id: str, falt: dict[str, Any]
    ) -> dict[str, Any]:
        andringar = normalisera_kunddata(falt)
        # Kolumnnamnen kommer ur KUNDDATA_FALT (allowlist i base.py), aldrig
        # ur anroparens nycklar — normalisera_kunddata har redan fällt allt
        # okänt, men SQL:en byggs ändå bara av namn vi själva skrivit.
        kolumner = [namn for namn in KUNDDATA_FALT if namn in andringar]
        if not kolumner:
            befintlig = await self.get_customer_details(tenant_id)
            if befintlig:
                return befintlig
            kolumner = []
        satta = ", ".join(
            f"{namn} = ${i + 2}" for i, namn in enumerate(kolumner)
        )
        varden = [andringar[namn] for namn in kolumner]
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                f"""
                insert into ss_customer_details (tenant_id{"".join("," + n for n in kolumner)})
                values ($1{"".join(f", ${i + 2}" for i in range(len(kolumner)))})
                on conflict (tenant_id) do update
                set {satta + ", " if satta else ""}updated_at = now()
                returning *
                """,
                tenant_id,
                *varden,
            )
        return _row(record)

    async def list_customer_contacts(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                select * from ss_customer_contacts
                where tenant_id = $1
                order by created_at
                """,
                tenant_id,
            )
        return [_row(r) for r in records]

    async def create_customer_contact(
        self,
        tenant_id: str,
        *,
        namn: str,
        roll: str | None = None,
        mejl: str | None = None,
        telefon: str | None = None,
    ) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                insert into ss_customer_contacts (tenant_id, namn, roll, mejl, telefon)
                values ($1, $2, $3, $4, $5)
                returning *
                """,
                tenant_id,
                namn.strip(),
                (roll or "").strip() or None,
                (mejl or "").strip() or None,
                (telefon or "").strip() or None,
            )
        return _row(record)

    async def update_customer_contact(
        self,
        tenant_id: str,
        contact_id: str,
        *,
        namn: str | None = None,
        roll: str | None = None,
        mejl: str | None = None,
        telefon: str | None = None,
    ) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                update ss_customer_contacts
                   set namn    = case when $3::text is not null and btrim($3) <> ''
                                      then btrim($3) else namn end,
                       roll    = case when $4::text is not null
                                      then nullif(btrim($4), '') else roll end,
                       mejl    = case when $5::text is not null
                                      then nullif(btrim($5), '') else mejl end,
                       telefon = case when $6::text is not null
                                      then nullif(btrim($6), '') else telefon end,
                       updated_at = now()
                 -- Båda villkoren: ett kontakt-id ur en annan kunds lista ska
                 -- ge 404, inte en uppdatering över tenant-gränsen.
                 where id = $2 and tenant_id = $1
                returning *
                """,
                tenant_id,
                contact_id,
                namn,
                roll,
                mejl,
                telefon,
            )
        return _row(record) if record else None

    async def delete_customer_contact(self, tenant_id: str, contact_id: str) -> bool:
        async with self.pool.acquire() as conn:
            resultat = await conn.execute(
                "delete from ss_customer_contacts where id = $1 and tenant_id = $2",
                contact_id,
                tenant_id,
            )
        return resultat.endswith("1")

    # -- Bokföring (migration 045) ------------------------------------------
    #
    # Samma validering som MemoryStorage, via de DELADE hjälparna i base.py.
    # Två kopior av ett check-villkor blir förr eller senare två olika
    # villkor — se AGENT_RUN_TYPES.

    async def create_bk_underlag(
        self,
        tenant_id: str,
        *,
        sha256: str,
        filnamn: str,
        mimetyp: str,
        status: str,
        datum: date | None = None,
        motpart: str | None = None,
        brutto: Decimal | None = None,
        momssats: Decimal | None = None,
        riktning: str | None = None,
        kategori: str | None = None,
        anmarkning: str = "",
    ) -> dict[str, Any]:
        kontrollera_bk_status(status)
        kontrollera_bk_riktning(riktning)
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into bk_underlag
                  (tenant_id, sha256, filnamn, mimetyp, status, datum, motpart,
                   brutto, momssats, riktning, kategori, anmarkning)
                values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                returning *
                """,
                tenant_id,
                sha256,
                filnamn,
                mimetyp,
                status,
                bk_datum(datum),
                motpart,
                bk_belopp(brutto, "brutto"),
                bk_belopp(momssats, "momssats"),
                riktning,
                kategori,
                anmarkning,
            )
        return _row(record)

    async def get_bk_underlag(self, tenant_id: str, underlag_id: str) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow("select * from bk_underlag where id = $1", underlag_id)
        return _row(record)

    async def get_bk_underlag_by_sha256(
        self, tenant_id: str, sha256: str
    ) -> dict[str, Any] | None:
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                "select * from bk_underlag where sha256 = $1 order by created_at limit 1",
                sha256,
            )
        return _row(record)

    async def list_bk_underlag(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from bk_underlag
                where (datum is null or $1::date is null or datum >= $1)
                  and (datum is null or $2::date is null or datum <= $2)
                order by datum nulls last, created_at
                limit $3
                """,
                bk_datum(fran),
                bk_datum(till),
                limit,
            )
        return [_row(r) for r in records]

    async def update_bk_underlag(
        self,
        tenant_id: str,
        underlag_id: str,
        *,
        status: str | None = None,
        datum: date | None = None,
        motpart: str | None = None,
        brutto: Decimal | None = None,
        momssats: Decimal | None = None,
        riktning: str | None = None,
        kategori: str | None = None,
        anmarkning: str | None = None,
    ) -> dict[str, Any] | None:
        if status is not None:
            kontrollera_bk_status(status)
        if riktning is not None:
            kontrollera_bk_riktning(riktning)

        # Dynamisk SET-lista: bara satta fält skrivs. Samma mönster som
        # update_prospect — en fast lista hade nollställt det anroparen
        # utelämnade, vilket för ett underlag betyder att en människas
        # rättelse raderar de fält hen inte rörde.
        satta: list[tuple[str, Any]] = []
        for kolumn, varde in (
            ("status", status),
            ("datum", bk_datum(datum)),
            ("motpart", motpart),
            ("brutto", bk_belopp(brutto, "brutto")),
            ("momssats", bk_belopp(momssats, "momssats")),
            ("riktning", riktning),
            ("kategori", kategori),
            ("anmarkning", anmarkning),
        ):
            if varde is not None:
                satta.append((kolumn, varde))

        if not satta:
            return await self.get_bk_underlag(tenant_id, underlag_id)

        set_sql = ", ".join(f"{kolumn} = ${i + 2}" for i, (kolumn, _) in enumerate(satta))
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                f"update bk_underlag set {set_sql} where id = $1 returning *",
                underlag_id,
                *[varde for _, varde in satta],
            )
        return _row(record)

    async def create_bk_verifikat(
        self,
        tenant_id: str,
        *,
        underlag_id: str,
        serie: str,
        nummer: str,
        datum: date,
        text: str,
        rader: list[dict[str, Any]],
    ) -> dict[str, Any]:
        kontrollera_bk_balans(rader)
        # EN transaktion för huvud och rader. _scoped öppnar redan en, så ett
        # fel på någon rad rullar tillbaka hela verifikatet — ett halvskrivet
        # verifikat balanserar inte och gör varje senare periodrapport fel.
        async with self._scoped(tenant_id) as conn:
            record = await conn.fetchrow(
                """
                insert into bk_verifikat (tenant_id, underlag_id, serie, nummer, datum, text)
                values ($1, $2, $3, $4, $5, $6)
                returning *
                """,
                tenant_id,
                underlag_id,
                serie,
                nummer,
                bk_datum(datum),
                text,
            )
            verifikat_id = record["id"]
            await conn.executemany(
                """
                insert into bk_verifikat_rad (tenant_id, verifikat_id, konto, debet, kredit, text)
                values ($1, $2, $3, $4, $5, $6)
                """,
                [
                    (
                        tenant_id,
                        verifikat_id,
                        str(rad["konto"]),
                        bk_belopp(rad.get("debet"), "debet") or Decimal(0),
                        bk_belopp(rad.get("kredit"), "kredit") or Decimal(0),
                        rad.get("text", ""),
                    )
                    for rad in rader
                ],
            )
            radposter = await conn.fetch(
                """
                select konto, debet, kredit, text from bk_verifikat_rad
                where verifikat_id = $1 order by id
                """,
                verifikat_id,
            )
        post = _row(record)
        post["rader"] = [dict(r) for r in radposter]
        return post

    async def list_bk_verifikat(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
    ) -> list[dict[str, Any]]:
        async with self._scoped(tenant_id) as conn:
            records = await conn.fetch(
                """
                select * from bk_verifikat
                where ($1::date is null or datum >= $1)
                  and ($2::date is null or datum <= $2)
                order by datum, nummer
                """,
                bk_datum(fran),
                bk_datum(till),
            )
            # EN fråga för raderna, inte en per verifikat: en period med 200
            # verifikat hade annars blivit 201 rundturer.
            radposter = await conn.fetch(
                """
                select r.verifikat_id, r.konto, r.debet, r.kredit, r.text
                from bk_verifikat_rad r
                join bk_verifikat v on v.id = r.verifikat_id
                where ($1::date is null or v.datum >= $1)
                  and ($2::date is null or v.datum <= $2)
                order by r.id
                """,
                bk_datum(fran),
                bk_datum(till),
            )

        per_verifikat: dict[str, list[dict[str, Any]]] = {}
        for rad in radposter:
            data = dict(rad)
            per_verifikat.setdefault(str(data.pop("verifikat_id")), []).append(data)

        poster = []
        for record in records:
            post = _row(record)
            post["rader"] = per_verifikat.get(post["id"], [])
            poster.append(post)
        return poster

    async def rensa_bk_period(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
    ) -> int:
        # Villkoret är ORDAGRANT `list_bk_underlag`:s, `datum is null`
        # inräknat. Skrivs det snävare här raderar knappen ett annat urval än
        # vyn visade, och kvar blir just de odaterade underlagen — de som
        # grinden fällt och som listan lyfter fram.
        #
        # bk_verifikat och bk_verifikat_rad följer med via `on delete cascade`
        # (migration 045). Ingen egen delete behövs, och en sådan hade dessutom
        # kunnat lämna rader efter sig om ordningen blev fel.
        #
        # `delete`-rättigheten finns sedan migration 045 — den skrevs in från
        # rad ett just för att en kodväg som behöver den annars svarar 500 i
        # drift medan sviten är grön mot minnet.
        async with self._scoped(tenant_id) as conn:
            status = await conn.execute(
                """
                delete from bk_underlag
                where (datum is null or $1::date is null or datum >= $1)
                  and (datum is null or $2::date is null or datum <= $2)
                """,
                bk_datum(fran),
                bk_datum(till),
            )
        # asyncpg ger tillbaka kommandotaggen, "DELETE <n>".
        return int(status.rsplit(" ", 1)[-1])

    async def close(self) -> None:
        await self.pool.close()
