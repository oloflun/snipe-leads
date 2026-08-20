"""In-memory-lagring (multi-tenant) med samma gränssnitt som PostgresStorage.

Används när DATABASE_URL saknas eller databasen inte går att nå. All data
partitioneras per tenant: kunder, ärenden, kunskapsbas och API-nycklar är
helt isolerade mellan tenants, precis som RLS-policyerna i Postgres-läget.
Default-tenanten (Nordlys Handel) seedas med demo-kunskapsbasen.
"""

import hashlib
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import (
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
    DEFAULT_TENANT_SLUG,
    PUBLIC_DEMO_TENANT_ID,
    PUBLIC_DEMO_TENANT_NAME,
    PUBLIC_DEMO_TENANT_SLUG,
)
from ..kb_articles import DEMO_KB_ARTICLES, KB_ARTICLES
from .base import AGENT_RUN_TYPES, status_transition_allowed

_STOPWORDS = {
    "och", "att", "det", "som", "en", "ett", "jag", "har", "min", "mitt", "mina",
    "den", "med", "för", "inte", "på", "är", "av", "om", "till", "kan", "ni",
    "vad", "hur", "när", "var", "vill", "skulle", "hej", "tack", "mvh", "man",
    "får", "blir", "vara", "denna", "detta", "era", "er", "din", "ditt",
}

_GLOBAL_CHANNEL_CONFIGS = {
    "web": {"channel": "web", "tone": "halvformell, vänlig och lösningsorienterad", "max_length": 1500},
    "email": {"channel": "email", "tone": "formell, professionell och tydlig", "max_length": 2500},
    "whatsapp": {"channel": "whatsapp", "tone": "kortfattad och vardaglig men artig", "max_length": 800},
}


def _tokenize(text: str) -> set[str]:
    text = unicodedata.normalize("NFC", text.lower())
    tokens = re.findall(r"[a-zåäöé0-9]{3,}", text)
    # Grov stamning: kapa vanliga svenska ändelser så "leveransen" matchar "leverans".
    stemmed = set()
    for token in tokens:
        if token in _STOPWORDS:
            continue
        for suffix in ("arna", "erna", "orna", "ande", "ende", "aste", "en", "et", "ar", "er", "or", "na", "a", "s"):
            if len(token) > 4 and token.endswith(suffix):
                token = token[: -len(suffix)]
                break
        stemmed.add(token)
    return stemmed


# Kundens ord är sällan artikelns ord. "Vad kostar den?" besvaras av en artikel
# som heter "Priser och offert", och den grova stamningen gör det värre:
# "kostar" kapas till "kost", som är för kort för prefixmatchning och dessutom
# ett helt annat ord. Frågan hittade därför ingenting och lämnades över trots
# att svaret fanns.
#
# Utvidgningen sker BARA på frågesidan och kan bara lägga till kandidater.
# Att den inte kan orsaka fel svar beror på fackfiltret i sim_agent: en
# tillagd kandidat används ändå bara om den hör till ärendets fack.
_QUERY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "kost": ("pris", "kostnad"),          # "kostar" → "kost" efter stamning
    "kostnad": ("pris",),
    "pris": ("kostnad",),
    "delbetal": ("delbetalning", "avbetalning", "faktur"),
    "avbetal": ("delbetalning",),
    "fraktbolag": ("frakt", "leverans"),
    "frakt": ("leverans",),
    "leverans": ("frakt",),
    "snabbt": ("leveranstid", "arbetsdag"),
    "ångra": ("ångerrätt", "öppet köp", "retur"),
    "byta": ("retur", "reklamation"),
    "trasig": ("reklamation", "skadad"),
    "kurs": ("utbildning",),
    "utbildning": ("kurs",),
}


def _expand_query(tokens: set[str]) -> set[str]:
    """Frågans tokens plus kända synonymer. Rör aldrig artiklarnas tokens."""
    expanded = set(tokens)
    for token in tokens:
        expanded.update(_QUERY_SYNONYMS.get(token, ()))
    return expanded


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _kb_row(tenant_id: str, article: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "title": article["title"],
        "content": article["content"],
        "category": article["category"],
        "tokens": _tokenize(article["title"] + " " + article["content"]),
        "title_tokens": _tokenize(article["title"]),
        "created_at": _now(),
    }


class MemoryStorage:
    name = "memory"

    def __init__(self) -> None:
        self.tenants: dict[str, dict[str, Any]] = {}
        self.customers: dict[str, dict[str, Any]] = {}
        # (tenant_id, typ, värde) → customer_id: samma e-post kan finnas hos flera tenants.
        self.identifiers: dict[tuple[str, str, str], str] = {}
        self.tickets: dict[str, dict[str, Any]] = {}
        # ticket_id → insättningsnummer. Håller ordningen stabil när flera
        # ärenden delar created_at. Ligger BREDVID ärendet och inte i det, så
        # att ett internt sorteringshjälpmedel inte läcker ut i API-svar.
        self._ticket_order: dict[str, int] = {}
        self.conversations: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, list[dict[str, Any]]] = {}
        self.metrics: list[dict[str, Any]] = []
        self.api_keys: dict[str, dict[str, Any]] = {}
        self.kb: dict[str, list[dict[str, Any]]] = {}
        self.channel_overrides: dict[tuple[str, str], dict[str, Any]] = {}
        self.taxonomy_overrides: dict[str, tuple[str, ...]] = {}
        self.context_docs: dict[str, list[dict[str, Any]]] = {}
        # Leads Fas C-E (Del J/scheduler). Ingen API-yta bygger dessa än
        # (Fas C-E:s persistenslager är en egen, senare ökning) — seedas
        # direkt i tester tills vidare.
        self.send_queue: dict[str, list[dict[str, Any]]] = {}
        # Avregistreringar, tenant-skopade. Motsvarar public.suppressions med
        # tenant_id från migration 030.
        self.suppressions: dict[str, list[dict[str, Any]]] = {}
        self.outreach_threads: dict[str, dict[str, dict[str, Any]]] = {}
        self.outreach_messages: dict[str, list[dict[str, Any]]] = {}
        # G11: (tenant_id, segment, lever) -> {sent, replies, positive}. Seedas
        # direkt i tester — ingen API-yta skriver hit än (samma status som
        # send_queue/outreach_* ovan).
        self.ab_results: list[dict[str, Any]] = []
        self.prospects: dict[str, list[dict[str, Any]]] = {}
        self.prospect_sources: dict[str, list[dict[str, Any]]] = {}
        self.agent_runs: dict[str, list[dict[str, Any]]] = {}
        # (scope_kind, scope_id, kind) -> tidsstämplar. Inte tenant-nycklad,
        # eftersom demons IP-scope inte har någon tenant (migration 019).
        self.rate_events: dict[tuple[str, str, str], list[datetime]] = {}
        # (tenant_id, agent_type) -> agent_configs.settings (migration 023)
        self.agent_settings: dict[tuple[str, str], dict[str, Any]] = {}
        # Plattformsnivå, inte tenant-nycklad: ett fel i proxyn eller i
        # schemaläggaren innan den vet vilken kund det gäller hör hemma här
        # också (migration 026, tenant_id nullable).
        self.platform_events: list[dict[str, Any]] = []
        # Nycklad på manifest_hash, inte tenant_id — delad baselinekatalog
        # (migration 016). Samma undantag som segmentaggregatet.
        self.skill_files: dict[str, list[dict[str, Any]]] = {}

        # Email-pipeline
        # In-memory-läget har inga riktiga inkorgar — mock-mail matas in direkt
        # via /api/inbox. Dicten finns för att lagringsgränssnittet ska vara
        # detsamma i båda lägena.
        self.mailboxes: dict[str, dict[str, Any]] = {}
        self.emails: dict[str, dict[str, Any]] = {}
        self.email_dedupe: set[tuple[str, str]] = set()  # (tenant_id, provider_message_id)
        self.attachments: dict[str, list[dict[str, Any]]] = {}  # email_id → [...]
        self.classifications: dict[str, dict[str, Any]] = {}  # email_id → senaste
        self.drafts: dict[str, dict[str, Any]] = {}
        self.drafts_by_email: dict[str, str] = {}  # email_id → draft_id
        self.reviews: list[dict[str, Any]] = []
        self.category_rules: dict[tuple[str, str], str] = {}  # (tenant_id, category) → mode
        self.decisions: list[dict[str, Any]] = []

        # Default-tenanten med demo-kunskapsbasen (motsvarar migrationens backfill + seed).
        self.tenants[DEFAULT_TENANT_ID] = {
            "id": DEFAULT_TENANT_ID,
            "slug": DEFAULT_TENANT_SLUG,
            "name": DEFAULT_TENANT_NAME,
            "active": True,
            "created_at": _now(),
        }
        self.kb[DEFAULT_TENANT_ID] = [_kb_row(DEFAULT_TENANT_ID, a) for a in KB_ARTICLES]

        # G8: den publika demons egen, isolerade tenant + KB.
        self.tenants[PUBLIC_DEMO_TENANT_ID] = {
            "id": PUBLIC_DEMO_TENANT_ID,
            "slug": PUBLIC_DEMO_TENANT_SLUG,
            "name": PUBLIC_DEMO_TENANT_NAME,
            "active": True,
            "created_at": _now(),
        }
        self.kb[PUBLIC_DEMO_TENANT_ID] = [
            _kb_row(PUBLIC_DEMO_TENANT_ID, a) for a in DEMO_KB_ARTICLES
        ]

    # -- Tenants ------------------------------------------------------------

    async def create_tenant(self, *, slug: str, name: str) -> dict[str, Any]:
        for tenant in self.tenants.values():
            if tenant["slug"] == slug:
                return tenant
        tenant = {
            "id": str(uuid.uuid4()),
            "slug": slug,
            "name": name,
            "active": True,
            "created_at": _now(),
        }
        self.tenants[tenant["id"]] = tenant
        self.kb.setdefault(tenant["id"], [])
        return tenant

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        return self.tenants.get(tenant_id)

    async def list_tenants(self) -> list[dict[str, Any]]:
        return [t for t in self.tenants.values() if t.get("active", True)]

    # -- Inkorgar -----------------------------------------------------------

    async def list_mailboxes(self, tenant_id: str) -> list[dict[str, Any]]:
        return [m for m in self.mailboxes.values() if m["tenant_id"] == tenant_id]

    # -- Kunddata -----------------------------------------------------------

    async def find_or_create_customer(
        self, tenant_id: str, *, email: str | None, phone: str | None, name: str | None
    ) -> dict[str, Any]:
        for id_type, value in (("email", email), ("phone", phone)):
            if value and (tenant_id, id_type, value.lower()) in self.identifiers:
                customer = self.customers[self.identifiers[(tenant_id, id_type, value.lower())]]
                if name and not customer.get("name"):
                    customer["name"] = name
                return customer
        customer = {"id": str(uuid.uuid4()), "tenant_id": tenant_id, "name": name, "created_at": _now()}
        self.customers[customer["id"]] = customer
        for id_type, value in (("email", email), ("phone", phone)):
            if value:
                self.identifiers[(tenant_id, id_type, value.lower())] = customer["id"]
        return customer

    async def get_customer_history(
        self, tenant_id: str, customer_id: str
    ) -> list[dict[str, Any]]:
        # Tiebreakern är INSÄTTNINGSORDNINGEN, inte id:t. Skillnaden är hela
        # poängen: `created_at` kommer från `datetime.now()`, vars upplösning
        # inte räcker när sex ärenden skapas i en snabb loop — på Windows kan
        # flera hamna på samma mikrosekund. Ordningen mellan dem blev då
        # godtycklig, och `history[:MAX_HISTORY_TICKETS]` i support_agent
        # plockade FEL tre ärenden. Agenten läste samtalet i skakad ordning
        # och trodde att kunden frågat något innan de gjort det.
        #
        # Ett första försök bröt likheter på `id`. Det var fel och värt att
        # skriva ut: id är ett slumpat uuid4, så ordningen blev deterministisk
        # inom en körning men fortfarande godtycklig mellan körningar — ett
        # flakigt test i stället för ett trasigt, vilket är sämre eftersom det
        # ser fixat ut.
        return sorted(
            (
                t for t in self.tickets.values()
                if t["customer_id"] == customer_id and t["tenant_id"] == tenant_id
            ),
            key=lambda t: (t["created_at"], self._ticket_order.get(t["id"], 0)),
            reverse=True,
        )

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
        ticket = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "subject": subject,
            "category": category,
            "status": "open",
            "priority": priority,
            "escalation_reason": None,
            "channel": channel,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.tickets[ticket["id"]] = ticket
        self._ticket_order[ticket["id"]] = len(self._ticket_order)
        conversation = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "ticket_id": ticket["id"],
            "channel": channel,
        }
        self.conversations[conversation["id"]] = conversation
        ticket["conversation_id"] = conversation["id"]
        return ticket

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> dict[str, Any] | None:
        ticket = self.tickets.get(ticket_id)
        if ticket and ticket["tenant_id"] == tenant_id:
            return {**ticket, "messages": self.messages.get(ticket["conversation_id"], [])}
        return None

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
        ticket = self.tickets.get(ticket_id)
        if not ticket or ticket["tenant_id"] != tenant_id:
            return None
        if status and status_transition_allowed(ticket["status"], status):
            ticket["status"] = status
        if category:
            ticket["category"] = category
        if priority:
            ticket["priority"] = priority
        if escalation_reason:
            ticket["escalation_reason"] = escalation_reason
        ticket["updated_at"] = _now()
        return ticket

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
        conversation = self.conversations.get(conversation_id)
        if not conversation or conversation["tenant_id"] != tenant_id:
            raise ValueError("Konversationen tillhör inte denna tenant.")
        message = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "direction": direction,
            "content": content,
            "sentiment": sentiment,
            "has_image": has_image,
            "created_at": _now(),
        }
        self.messages.setdefault(conversation_id, []).append(message)
        return message

    async def get_messages(
        self, tenant_id: str, conversation_id: str
    ) -> list[dict[str, Any]]:
        conversation = self.conversations.get(conversation_id)
        if not conversation or conversation["tenant_id"] != tenant_id:
            return []
        return self.messages.get(conversation_id, [])

    # -- Kunskapsbas --------------------------------------------------------

    async def search_kb(
        self,
        tenant_id: str,
        query: str,
        embedding: list[float] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        # OBS: `embedding` ignoreras helt här — ren tokenöverlappning, aldrig
        # semantisk. Missar synonymer/ordformer ("betalsätt" mot
        # "Betalningsmetoder" delar inga tokens). Upptäckt 2026-08-07 när en
        # Gemini-embeddingnyckel sattes och en KB-sökbugg INTE försvann — den
        # gick att spåra hit, inte till PostgresStorage (som faktiskt kör
        # pgvector-cosine-likhet, se postgres.py). Kvalitetstester av
        # KB-sökning mot MemoryStorage bevisar därför ingenting om
        # embeddings-kvalitet — de måste köras mot PostgresStorage.
        query_tokens = _expand_query(_tokenize(query))
        if not query_tokens:
            return []
        scored = []
        for article in self.kb.get(tenant_id, []):
            overlap = len(query_tokens & article["tokens"])
            title_overlap = len(query_tokens & article["title_tokens"])
            if overlap:
                # Titelträffar väger dubbelt så att rätt artikel vinner vid likvärdigt innehåll.
                scored.append(((overlap + 2 * title_overlap) / len(query_tokens), article))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {"id": a["id"], "title": a["title"], "content": a["content"],
             "category": a["category"], "similarity": round(score, 2)}
            for score, a in scored[:limit]
            # Tröskeln var 0.2. Sedan svaret måste komma ur ärendets fack
            # (article_in_category) kostar en svag träff inget: den kan bara
            # användas om den ändå hör till rätt fack. Lägre tröskel ger därför
            # fler chanser att hitta RÄTT artikel utan att öppna för fel svar —
            # frågor som "hur snabbt kommer varan" föll tidigare mellan stolarna.
            if score >= 0.12
        ]

    async def list_kb(self, tenant_id: str) -> list[dict[str, Any]]:
        return [
            {"id": a["id"], "title": a["title"], "content": a["content"],
             "category": a["category"], "created_at": a["created_at"]}
            for a in self.kb.get(tenant_id, [])
        ]

    async def add_kb_article(
        self,
        tenant_id: str,
        *,
        title: str,
        content: str,
        category: str,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        row = _kb_row(tenant_id, {"title": title, "content": content, "category": category})
        self.kb.setdefault(tenant_id, []).append(row)
        return {"id": row["id"], "title": title, "category": category}

    # -- Kanaler & metrics --------------------------------------------------

    async def get_channel_config(self, tenant_id: str, channel: str) -> dict[str, Any]:
        override = self.channel_overrides.get((tenant_id, channel))
        if override:
            return override
        return _GLOBAL_CHANNEL_CONFIGS.get(channel, _GLOBAL_CHANNEL_CONFIGS["web"])

    async def save_context_doc(
        self, tenant_id: str, *, kind: str, content: str, source: str = ""
    ) -> dict[str, Any]:
        existing = [d for d in self.context_docs.get(tenant_id, []) if d["kind"] == kind]
        version = max((d["version"] for d in existing), default=0) + 1
        doc = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "kind": kind,
            "content": content,
            "source": source,
            "version": version,
            "created_at": _now(),
        }
        self.context_docs.setdefault(tenant_id, []).append(doc)
        return doc

    async def list_context_docs(
        self, tenant_id: str, *, kind: str | None = None
    ) -> list[dict[str, Any]]:
        docs = self.context_docs.get(tenant_id, [])
        if kind:
            docs = [d for d in docs if d["kind"] == kind]
        return sorted(docs, key=lambda d: d["created_at"], reverse=True)

    async def get_latest_context_doc(self, tenant_id: str, *, kind: str) -> dict[str, Any] | None:
        docs = [d for d in self.context_docs.get(tenant_id, []) if d["kind"] == kind]
        if not docs:
            return None
        return max(docs, key=lambda d: d["version"])

    async def list_due_send_queue(self, tenant_id: str, now) -> list[dict[str, Any]]:
        return [
            item
            for item in self.send_queue.get(tenant_id, [])
            if item["status"] == "queued" and item["scheduled_at"] <= now
        ]

    async def update_send_queue_status(
        self, tenant_id: str, item_id: str, *, status: str, gate_checks: dict[str, Any]
    ) -> None:
        for item in self.send_queue.get(tenant_id, []):
            if item["id"] == item_id:
                item["status"] = status
                item["gate_checks"] = gate_checks
                return

    async def get_outreach_thread(self, tenant_id: str, thread_id: str) -> dict[str, Any] | None:
        return self.outreach_threads.get(tenant_id, {}).get(thread_id)

    # -- Underlaget send_guard dömer på (DEL 2.3) ---------------------------
    # Samma signaturer och samma normalisering som PostgresStorage. Skiljer de
    # sig åt är minnesvägen en lögn om vad produktionen gör.

    async def list_suppressions(self, tenant_id: str) -> set[str]:
        return {
            str(rad["email"]).strip().casefold()
            for rad in self.suppressions.get(tenant_id, [])
        }

    async def add_suppression(self, tenant_id: str, *, email: str, reason: str) -> None:
        adress = str(email or "").strip().casefold()
        if not adress:
            raise ValueError("add_suppression kräver en e-postadress.")
        rader = self.suppressions.setdefault(tenant_id, [])
        if any(str(r["email"]).strip().casefold() == adress for r in rader):
            return  # Idempotent: en andra avregistrering är inte ett fel.
        rader.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "email": adress,
                "reason": reason,
                "created_at": datetime.now(timezone.utc),
            }
        )

    async def count_sent_outreach(self, tenant_id: str, *, since=None) -> int:
        return sum(
            1
            for m in self.outreach_messages.get(tenant_id, [])
            if m.get("direction") == "outbound"
            and m.get("sent_at") is not None
            and (since is None or m["sent_at"] >= since)
        )

    async def last_contact_with_company(self, tenant_id: str, foretagsnyckel: str):
        if not foretagsnyckel:
            return None
        tidpunkter = [
            m["sent_at"]
            for m in self.outreach_messages.get(tenant_id, [])
            if m.get("direction") == "outbound"
            and m.get("sent_at") is not None
            and m.get("foretagsnyckel") == foretagsnyckel
        ]
        return max(tidpunkter) if tidpunkter else None

    async def get_pending_outreach_message(
        self, tenant_id: str, thread_id: str
    ) -> dict[str, Any] | None:
        candidates = [
            m
            for m in self.outreach_messages.get(tenant_id, [])
            if m["thread_id"] == thread_id and m["direction"] == "outbound" and m["sent_at"] is None
        ]
        return candidates[0] if candidates else None

    async def mark_outreach_message_sent(self, tenant_id: str, message_id: str, sent_at) -> None:
        for message in self.outreach_messages.get(tenant_id, []):
            if message["id"] == message_id:
                message["sent_at"] = sent_at
                return

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
        message = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "thread_id": thread_id,
            "direction": "outbound",
            "body": body,
            "subject": subject,
            "humanizer_variant": humanizer_variant,
            "sent_at": None,
        }
        queue_item = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "thread_id": thread_id,
            "scheduled_at": scheduled_at,
            "status": status,
            "gate_checks": {},
        }
        self.outreach_messages.setdefault(tenant_id, []).append(message)
        self.send_queue.setdefault(tenant_id, []).append(queue_item)
        return {"message": message, "queue_item": queue_item}

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
        prospect = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "company_name": company_name,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "language_state": "sv",
            "status": "new",
            "origin": origin,
            # Samma allowlist som Postgres-lagringen. Att spegla den här är inte
            # dubbelarbete: sviten kör mot minnet, och ett fält som tyst faller
            # bort i den ena lagringen hade gett gröna tester mot en vy som är
            # tom i drift.
            **{
                namn: värde
                for namn, värde in (profil or {}).items()
                if namn in ("orgnr", "ort", "postnr", "sni", "website", "anstallda", "omsattning")
                and värde is not None
            },
            "created_at": _now(),
        }
        self.prospects.setdefault(tenant_id, []).append(prospect)
        return prospect

    async def get_prospect(self, tenant_id: str, prospect_id: str) -> dict[str, Any] | None:
        return next(
            (p for p in self.prospects.get(tenant_id, []) if p["id"] == prospect_id), None
        )

    async def list_prospects(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return sorted(
            self.prospects.get(tenant_id, []), key=lambda p: p["created_at"], reverse=True
        )[:limit]

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
        prospect = await self.get_prospect(tenant_id, prospect_id)
        if not prospect:
            return None
        for field, value in (
            ("status", status),
            ("icp_fit", icp_fit),
            ("qualified", qualified),
            ("disqualifiers", disqualifiers),
        ):
            if value is not None:
                prospect[field] = value
        return prospect

    async def create_prospect_source(
        self,
        tenant_id: str,
        *,
        prospect_id: str,
        source_url: str,
        source_type: str,
        lawful_basis: str,
    ) -> dict[str, Any]:
        source = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "prospect_id": prospect_id,
            "source_url": source_url,
            "source_type": source_type,
            "lawful_basis": lawful_basis,
            "retrieved_at": _now(),
        }
        self.prospect_sources.setdefault(tenant_id, []).append(source)
        return source

    async def list_prospect_source_urls(self, tenant_id: str, prospect_id: str) -> set[str]:
        return {
            s["source_url"]
            for s in self.prospect_sources.get(tenant_id, [])
            if s["prospect_id"] == prospect_id
        }

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
        is_test: bool = False,
    ) -> dict[str, Any]:
        # Samma värdemängd som check-villkoret i migration 025. Utan den här
        # raden tar minnet emot vad som helst medan Postgres kastar — och det
        # är exakt hur "ingen leads-körning har någonsin sparats" kunde vara
        # sant i ett halvår med grön testsvit.
        if agent_type not in AGENT_RUN_TYPES:
            raise ValueError(
                f"agent_type={agent_type!r} finns inte i agent_runs check-villkoret "
                f"{AGENT_RUN_TYPES}. Mot Postgres hade det här kastat check-violation."
            )
        run = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "agent_type": agent_type,
            "is_test": is_test,
            "pack_version": pack_version,
            "skills_used": skills_used,
            "input": input_text,
            "output": output_text,
            "step_log": step_log,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "created_at": _now(),
        }
        self.agent_runs.setdefault(tenant_id, []).append(run)
        return run

    async def list_agent_runs(
        self, tenant_id: str, *, agent_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        runs = self.agent_runs.get(tenant_id, [])
        if agent_type:
            runs = [r for r in runs if r["agent_type"] == agent_type]
        return sorted(runs, key=lambda r: r["created_at"], reverse=True)[:limit]

    async def list_skill_files(self, *, manifest_hash: str) -> list[dict[str, Any]]:
        return list(self.skill_files.get(manifest_hash, []))

    async def publish_skill_files(
        self, *, manifest_hash: str, rows: list[dict[str, Any]], published_by: str = ""
    ) -> int:
        existing = self.skill_files.setdefault(manifest_hash, [])
        seen = {(r["namespace"], r["relative_path"]) for r in existing}
        added = 0
        for row in rows:
            key = (row["namespace"], row["relative_path"])
            if key in seen:
                continue  # samma idempotens som unique-villkoret i migration 016
            existing.append({**row, "published_by": published_by})
            seen.add(key)
            added += 1
        return added

    async def get_segment_ab_aggregate(self) -> list[dict[str, Any]]:
        from ..leads.segment_aggregate import AbResultRow, compute_segment_aggregate

        rows = [
            AbResultRow(
                tenant_id=r["tenant_id"],
                segment=r["segment"],
                lever=r["lever"],
                sent=r["sent"],
                replies=r["replies"],
                positive=r["positive"],
            )
            for r in self.ab_results
        ]
        aggregated = compute_segment_aggregate(rows)
        return [
            {
                "segment": a.segment,
                "lever": a.lever,
                "tenant_count": a.tenant_count,
                "sent": a.sent,
                "replies": a.replies,
                "positive": a.positive,
            }
            for a in aggregated
        ]

    async def get_agent_taxonomy(self, tenant_id: str) -> tuple[str, ...]:
        # A4: taxonomy_overrides finns för test/simuleringsläge. Postgres-läget
        # läser den riktiga agent_configs-tabellen (se PostgresStorage).
        from ..config import CATEGORIES

        override = self.taxonomy_overrides.get(tenant_id)
        return tuple(override) if override else CATEGORIES

    async def log_metric(
        self, tenant_id: str, *, ticket_id: str | None, metric_name: str, value: float | None
    ) -> None:
        self.metrics.append(
            {"tenant_id": tenant_id, "ticket_id": ticket_id, "metric_name": metric_name,
             "value": value, "created_at": _now()}
        )

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
        dedupe_key = (tenant_id, provider_message_id)
        if dedupe_key in self.email_dedupe:
            return None
        self.email_dedupe.add(dedupe_key)
        email = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "provider": provider,
            "provider_message_id": provider_message_id,
            "from_email": from_email,
            "from_name": from_name,
            "subject": subject,
            "body_text": body_text,
            "received_at": received_at or _now(),
            "status": "new",
            "ticket_id": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.emails[email["id"]] = email
        return email

    async def delete_emails_by_provider(self, tenant_id: str, provider: str) -> int:
        """Se Storage.delete_emails_by_provider.

        Dedupe-nyckeln tas bort med mailet. Utan det hade samma
        provider_message_id räknats som dublett i all framtid, och ett nytt
        urval testmail hade tyst blivit noll mail.
        """
        träffar = [
            email
            for email in self.emails.values()
            if email["tenant_id"] == tenant_id and email["provider"] == provider
        ]
        for email in träffar:
            self.emails.pop(email["id"], None)
            self.email_dedupe.discard((tenant_id, email["provider_message_id"]))
            self.classifications.pop(email["id"], None)
            draft_id = self.drafts_by_email.pop(email["id"], None)
            if draft_id:
                self.drafts.pop(draft_id, None)
        return len(träffar)

    def _email_summary(self, email: dict[str, Any]) -> dict[str, Any]:
        classification = self.classifications.get(email["id"])
        draft_id = self.drafts_by_email.get(email["id"])
        draft = self.drafts.get(draft_id) if draft_id else None
        return {
            **email,
            "classification": classification,
            "draft": draft,
            "attachment_count": len(self.attachments.get(email["id"], [])),
            "has_image": any(a["is_image"] for a in self.attachments.get(email["id"], [])),
        }

    async def list_emails(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        rows = [e for e in self.emails.values() if e["tenant_id"] == tenant_id]
        rows.sort(key=lambda e: e["received_at"], reverse=True)
        result = []
        needle = (search or "").lower()
        for email in rows:
            summary = self._email_summary(email)
            if status and summary["status"] != status:
                continue
            if category and (
                not summary["classification"]
                or summary["classification"]["category"] != category
            ):
                continue
            if needle and needle not in (
                email["subject"] + " " + email["body_text"] + " " + email["from_email"]
                + " " + (email["from_name"] or "")
            ).lower():
                continue
            result.append(summary)
            if len(result) >= limit:
                break
        return result

    async def get_email(self, tenant_id: str, email_id: str) -> dict[str, Any] | None:
        email = self.emails.get(email_id)
        if not email or email["tenant_id"] != tenant_id:
            return None
        summary = self._email_summary(email)
        summary["attachments"] = self.attachments.get(email_id, [])
        summary["decisions"] = await self.list_decisions(tenant_id, email_id)
        return summary

    async def update_email(
        self,
        tenant_id: str,
        email_id: str,
        *,
        status: str | None = None,
        ticket_id: str | None = None,
    ) -> dict[str, Any] | None:
        email = self.emails.get(email_id)
        if not email or email["tenant_id"] != tenant_id:
            return None
        if status:
            email["status"] = status
        if ticket_id:
            email["ticket_id"] = ticket_id
        email["updated_at"] = _now()
        return email

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
        attachment = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "email_id": email_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "data_url": data_url,
            "is_image": is_image,
            "created_at": _now(),
        }
        self.attachments.setdefault(email_id, []).append(attachment)
        return attachment

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
        classification = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "email_id": email_id,
            "category": category,
            "priority": priority,
            "sentiment": sentiment,
            "confidence": confidence,
            "escalate": escalate,
            "escalation_reason": escalation_reason,
            "reasoning": reasoning,
            "kb_sources": kb_sources,
            "model": model,
            "created_at": _now(),
        }
        self.classifications[email_id] = classification
        return classification

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
        draft = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "email_id": email_id,
            "ticket_id": ticket_id,
            "content": content,
            "status": status,
            "auto": auto,
            "confidence": confidence,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.drafts[draft["id"]] = draft
        self.drafts_by_email[email_id] = draft["id"]
        return draft

    async def get_draft(self, tenant_id: str, draft_id: str) -> dict[str, Any] | None:
        draft = self.drafts.get(draft_id)
        if draft and draft["tenant_id"] == tenant_id:
            return draft
        return None

    async def update_draft(
        self,
        tenant_id: str,
        draft_id: str,
        *,
        status: str | None = None,
        content: str | None = None,
    ) -> dict[str, Any] | None:
        draft = self.drafts.get(draft_id)
        if not draft or draft["tenant_id"] != tenant_id:
            return None
        if status:
            draft["status"] = status
        if content is not None:
            draft["content"] = content
        draft["updated_at"] = _now()
        return draft

    async def add_review(
        self,
        tenant_id: str,
        *,
        draft_id: str,
        action: str,
        edited_content: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        review = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "draft_id": draft_id,
            "action": action,
            "edited_content": edited_content,
            "note": note,
            "created_at": _now(),
        }
        self.reviews.append(review)
        return review

    async def get_category_rules(self, tenant_id: str) -> dict[str, str]:
        from ..config import DEFAULT_CATEGORY_RULES

        rules = dict(DEFAULT_CATEGORY_RULES)
        for (rule_tenant, category), mode in self.category_rules.items():
            if rule_tenant == tenant_id:
                rules[category] = mode
        return rules

    async def set_category_rule(self, tenant_id: str, category: str, mode: str) -> None:
        self.category_rules[(tenant_id, category)] = mode

    async def log_decision(
        self, tenant_id: str, *, email_id: str | None, event: str, detail: dict[str, Any]
    ) -> None:
        self.decisions.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "email_id": email_id,
                "event": event,
                "detail": detail,
                "created_at": _now(),
            }
        )

    async def list_decisions(
        self, tenant_id: str, email_id: str
    ) -> list[dict[str, Any]]:
        return [
            d for d in self.decisions
            if d["tenant_id"] == tenant_id and d["email_id"] == email_id
        ]

    # -- API-nycklar --------------------------------------------------------

    async def validate_api_key(self, raw_key: str) -> dict[str, Any] | None:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        record = self.api_keys.get(key_hash)
        if record and record["active"]:
            tenant = self.tenants.get(record["tenant_id"])
            if not tenant or not tenant["active"]:
                return None
            record["last_used_at"] = _now()
            return record
        return None

    async def create_api_key(
        self, tenant_id: str, *, tenant_name: str, raw_key: str
    ) -> dict[str, Any]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        record = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "key_prefix": raw_key[:12],
            "active": True,
            "created_at": _now(),
            "last_used_at": None,
        }
        self.api_keys[key_hash] = record
        return record

    async def list_outreach_messages(
        self, tenant_id: str, thread_id: str
    ) -> list[dict[str, Any]]:
        return [
            m for m in self.outreach_messages.get(tenant_id, []) if m["thread_id"] == thread_id
        ]

    # -- Agentkonfiguration (autonomi + ICP) --------------------------------

    async def get_agent_settings(self, tenant_id: str, *, agent_type: str) -> dict[str, Any]:
        return dict(self.agent_settings.get((tenant_id, agent_type), {}))

    async def set_agent_settings(
        self, tenant_id: str, *, agent_type: str, settings: dict[str, Any]
    ) -> dict[str, Any]:
        self.agent_settings[(tenant_id, agent_type)] = dict(settings)
        return dict(settings)

    async def list_review_queue(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        items = [
            item
            for item in self.send_queue.get(tenant_id, [])
            if item["status"] == "awaiting_review"
        ]
        return items[:limit]

    # -- Rate limiting ------------------------------------------------------
    #
    # Speglar Postgres-beteendet, inklusive att räknaren INTE är tenant-skopad.
    # MemoryStorage får aldrig sacka efter protokollet — det var precis så
    # agent_runs.agent_type-buggen kunde gömma sig i ett halvår: villkoret
    # fanns bara i Postgres, och testerna körde mot minnet.

    async def count_rate_events(
        self, *, scope_kind: str, scope_id: str, kind: str, since: Any
    ) -> int:
        events = self.rate_events.get((scope_kind, scope_id, kind), [])
        return sum(1 for at in events if at >= since)

    async def record_rate_events(
        self, *, scope_kind: str, scope_id: str, kind: str, count: int
    ) -> None:
        if count <= 0:
            return
        now = datetime.now(timezone.utc)
        self.rate_events.setdefault((scope_kind, scope_id, kind), []).extend([now] * count)

    # -- Admin: cross-tenant-läsning (Fas 6) --------------------------------

    async def list_tenants_with_stats(self) -> list[dict[str, Any]]:
        rows = []
        for tenant in self.tenants.values():
            tid = tenant["id"]
            runs = self.agent_runs.get(tid, [])
            rows.append(
                {
                    **tenant,
                    "tickets": sum(1 for t in self.tickets.values() if t["tenant_id"] == tid),
                    "runs": len(runs),
                    "tokens_in": sum(r.get("tokens_in") or 0 for r in runs),
                    "tokens_out": sum(r.get("tokens_out") or 0 for r in runs),
                    "errors": sum(
                        1
                        for e in self.platform_events
                        if e["tenant_id"] == tid and e["level"] == "error"
                    ),
                    "last_activity": max((r["created_at"] for r in runs), default=None),
                }
            )
        return rows

    async def list_agent_runs_all(
        self,
        *,
        tenant_id: str | None = None,
        agent_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        runs = [
            run
            for tid, tenant_runs in self.agent_runs.items()
            if tenant_id is None or tid == tenant_id
            for run in tenant_runs
        ]
        if agent_type:
            runs = [r for r in runs if r["agent_type"] == agent_type]
        runs.sort(key=lambda r: r["created_at"], reverse=True)
        return runs[:limit]

    async def get_agent_run(self, run_id: str) -> dict[str, Any] | None:
        for tenant_runs in self.agent_runs.values():
            for run in tenant_runs:
                if run["id"] == run_id:
                    return run
        return None

    async def list_platform_events(
        self,
        *,
        level: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        events = list(self.platform_events)
        if level:
            events = [e for e in events if e["level"] == level]
        if tenant_id:
            events = [e for e in events if e["tenant_id"] == tenant_id]
        events.sort(key=lambda e: e["created_at"], reverse=True)
        return events[:limit]

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
        self.platform_events.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "level": level,
                "source": source,
                "message": message,
                "detail": detail or {},
                "run_id": run_id,
                "created_at": _now(),
            }
        )

    async def close(self) -> None:
        return None
