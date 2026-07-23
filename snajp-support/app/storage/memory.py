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

from ..config import DEFAULT_TENANT_ID, DEFAULT_TENANT_NAME, DEFAULT_TENANT_SLUG
from ..kb_articles import KB_ARTICLES
from .base import status_transition_allowed

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
        self.conversations: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, list[dict[str, Any]]] = {}
        self.metrics: list[dict[str, Any]] = []
        self.api_keys: dict[str, dict[str, Any]] = {}
        self.kb: dict[str, list[dict[str, Any]]] = {}
        self.channel_overrides: dict[tuple[str, str], dict[str, Any]] = {}

        # Default-tenanten med demo-kunskapsbasen (motsvarar migrationens backfill + seed).
        self.tenants[DEFAULT_TENANT_ID] = {
            "id": DEFAULT_TENANT_ID,
            "slug": DEFAULT_TENANT_SLUG,
            "name": DEFAULT_TENANT_NAME,
            "active": True,
            "created_at": _now(),
        }
        self.kb[DEFAULT_TENANT_ID] = [_kb_row(DEFAULT_TENANT_ID, a) for a in KB_ARTICLES]

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
        return sorted(
            (
                t for t in self.tickets.values()
                if t["customer_id"] == customer_id and t["tenant_id"] == tenant_id
            ),
            key=lambda t: t["created_at"],
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
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        query_tokens = _tokenize(query)
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
            if score >= 0.2
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

    async def log_metric(
        self, tenant_id: str, *, ticket_id: str | None, metric_name: str, value: float | None
    ) -> None:
        self.metrics.append(
            {"tenant_id": tenant_id, "ticket_id": ticket_id, "metric_name": metric_name,
             "value": value, "created_at": _now()}
        )

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

    async def close(self) -> None:
        return None
