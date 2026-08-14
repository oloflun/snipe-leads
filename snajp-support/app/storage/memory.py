"""In-memory-lagring (multi-tenant) med samma gränssnitt som PostgresStorage.

Används när DATABASE_URL saknas eller databasen inte går att nå. All data
partitioneras per tenant: kunder, ärenden, kunskapsbas och API-nycklar är
helt isolerade mellan tenants, precis som RLS-policyerna i Postgres-läget.
Default-tenanten (Nordlys Handel) seedas med demo-kunskapsbasen.
"""

import hashlib
import math
import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
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


_PREFIX_MIN = 5


def _matches(token: str, article_tokens: set[str]) -> bool:
    """Träffar ordet artikeln? Prefix-tolerant för svenska böjningar.

    "garanti", "garantin" och "garantitid" är samma sak för kunden men tre
    olika strängar. Prefixmatchning kräver fem tecken — kortare ger
    slumpträffar som "leve" i både "leverans" och "leverera".
    """
    if token in article_tokens:
        return True
    if len(token) < _PREFIX_MIN:
        return False
    return any(
        other.startswith(token) or (len(other) >= _PREFIX_MIN and token.startswith(other))
        for other in article_tokens
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tenant_row(tenant_id: str, slug: str, name: str) -> dict[str, Any]:
    """Samma kolumnuppsättning som ss_tenants efter 006 — inklusive de tomma
    self-service-fälten, så att API:t ser likadant ut i båda lägena."""
    return {
        "id": tenant_id,
        "slug": slug,
        "name": name,
        "company_name": None,
        "tone": None,
        "system_prompt_extra": None,
        "active": True,
        "created_at": _now(),
        "updated_at": _now(),
    }


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
        self.usage: list[dict[str, Any]] = []
        self.subscriptions: dict[str, dict[str, Any]] = {}
        self.api_keys: dict[str, dict[str, Any]] = {}
        self.kb: dict[str, list[dict[str, Any]]] = {}
        self.channel_overrides: dict[tuple[str, str], dict[str, Any]] = {}

        # Email-pipeline
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
        self.tenants[DEFAULT_TENANT_ID] = _tenant_row(
            DEFAULT_TENANT_ID, DEFAULT_TENANT_SLUG, DEFAULT_TENANT_NAME
        )
        self.kb[DEFAULT_TENANT_ID] = [_kb_row(DEFAULT_TENANT_ID, a) for a in KB_ARTICLES]

        # Demo och pilot är egna arbetsytor och ska aldrig kvotstoppas — samma
        # seed som i 010_snajp_subscriptions.sql.
        from ..config import PILOT_TENANT_ID

        for internal_id in (DEFAULT_TENANT_ID, PILOT_TENANT_ID):
            self.subscriptions[internal_id] = {
                "tenant_id": internal_id,
                "plan_id": "intern",
                "status": "active",
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
                "current_period_start": None,
                "current_period_end": None,
                "cancel_at_period_end": False,
                "created_at": _now(),
                "updated_at": _now(),
            }

    # -- Tenants ------------------------------------------------------------

    async def create_tenant(self, *, slug: str, name: str) -> dict[str, Any]:
        for tenant in self.tenants.values():
            if tenant["slug"] == slug:
                return tenant
        tenant = _tenant_row(str(uuid.uuid4()), slug, name)
        self.tenants[tenant["id"]] = tenant
        self.kb.setdefault(tenant["id"], [])
        return tenant

    async def ensure_tenant(
        self, tenant_id: str, *, slug: str, name: str
    ) -> dict[str, Any]:
        existing = self.tenants.get(tenant_id)
        if existing:
            return existing
        tenant = _tenant_row(tenant_id, slug, name)
        self.tenants[tenant_id] = tenant
        self.kb.setdefault(tenant_id, [])
        return tenant

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        return self.tenants.get(tenant_id)

    async def update_tenant(
        self,
        tenant_id: str,
        *,
        name: str | None = None,
        company_name: str | None = None,
        tone: str | None = None,
        system_prompt_extra: str | None = None,
    ) -> dict[str, Any] | None:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        for field, value in (
            ("name", name),
            ("company_name", company_name),
            ("tone", tone),
            ("system_prompt_extra", system_prompt_extra),
        ):
            if value is not None:
                tenant[field] = value
        tenant["updated_at"] = _now()
        return tenant

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
        articles = self.kb.get(tenant_id, [])
        if not query_tokens or not articles:
            return []

        # Sällsynta ord väger tyngre (IDF). Utan det vinner artiklar som råkar
        # dela många generiska ord med mailet — "hjärtstartare" förekommer i
        # nästan varje artikel och säger inget om vilken som är rätt, medan
        # "garantin" pekar direkt på en.
        total = len(articles)
        weights: dict[str, float] = {}
        for token in query_tokens:
            hits = sum(1 for a in articles if _matches(token, a["tokens"]))
            # +1 så att ett ord som finns i alla artiklar fortfarande väger något.
            weights[token] = math.log((total + 1) / (hits + 1)) + 0.1

        best_possible = sum(weights.values()) or 1.0
        scored = []
        for article in articles:
            score = 0.0
            for token in query_tokens:
                if _matches(token, article["tokens"]):
                    # Titelträffar räknas dubbelt — rubriken sammanfattar artikeln.
                    multiplier = 2.0 if _matches(token, article["title_tokens"]) else 1.0
                    score += weights[token] * multiplier
            if score:
                scored.append((min(score / best_possible, 1.0), article))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {"id": a["id"], "title": a["title"], "content": a["content"],
             "category": a["category"], "similarity": round(score, 2)}
            for score, a in scored[:limit]
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

    def _find_kb(self, tenant_id: str, article_id: str) -> dict[str, Any] | None:
        # Söker BARA i tenantens egen lista — en artikel hos en annan tenant är
        # osynlig här, precis som RLS-policyn gör den i Postgres-läget.
        for article in self.kb.get(tenant_id, []):
            if article["id"] == article_id:
                return article
        return None

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
        article = self._find_kb(tenant_id, article_id)
        if not article:
            return None
        if title is not None:
            article["title"] = title
        if content is not None:
            article["content"] = content
        if category is not None:
            article["category"] = category
        # Sökindexet är härlett ur texten och måste räknas om vid varje ändring,
        # annars söker agenten vidare på den gamla lydelsen.
        article["tokens"] = _tokenize(article["title"] + " " + article["content"])
        article["title_tokens"] = _tokenize(article["title"])
        return {
            "id": article["id"],
            "title": article["title"],
            "content": article["content"],
            "category": article["category"],
        }

    async def delete_kb_article(self, tenant_id: str, article_id: str) -> bool:
        article = self._find_kb(tenant_id, article_id)
        if not article:
            return False
        self.kb[tenant_id].remove(article)
        return True

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
        self.usage.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "kind": kind,
                "model": model,
                "simulated": simulated,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "responses": responses,
                "ticket_id": ticket_id,
                "email_id": email_id,
                "created_at": _now(),
            }
        )

    async def get_usage(self, tenant_id: str, *, days: int = 30) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = [
            r for r in self.usage
            if r["tenant_id"] == tenant_id
            and datetime.fromisoformat(r["created_at"]) >= cutoff
        ]
        per_kind: dict[str, dict[str, int]] = {}
        for row in rows:
            bucket = per_kind.setdefault(row["kind"], {"responses": 0, "total_tokens": 0})
            bucket["responses"] += row["responses"]
            bucket["total_tokens"] += row["total_tokens"]
        return {
            "days": days,
            "responses": sum(r["responses"] for r in rows),
            "prompt_tokens": sum(r["prompt_tokens"] for r in rows),
            "completion_tokens": sum(r["completion_tokens"] for r in rows),
            "total_tokens": sum(r["total_tokens"] for r in rows),
            "simulated_responses": sum(r["responses"] for r in rows if r["simulated"]),
            "per_kind": [
                {"kind": kind, **totals} for kind, totals in sorted(per_kind.items())
            ],
        }

    async def count_responses_since(self, tenant_id: str, since: str) -> int:
        cutoff = datetime.fromisoformat(since)
        return sum(
            row["responses"]
            for row in self.usage
            if row["tenant_id"] == tenant_id
            and datetime.fromisoformat(row["created_at"]) >= cutoff
        )

    # -- Abonnemang -----------------------------------------------------------

    async def get_subscription(self, tenant_id: str) -> dict[str, Any] | None:
        return self.subscriptions.get(tenant_id)

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
    ) -> dict[str, Any]:
        record = self.subscriptions.setdefault(
            tenant_id,
            {
                "tenant_id": tenant_id,
                "plan_id": "free",
                "status": "none",
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
                "current_period_start": None,
                "current_period_end": None,
                "cancel_at_period_end": False,
                "created_at": _now(),
            },
        )
        for field, value in (
            ("plan_id", plan_id),
            ("status", status),
            ("stripe_customer_id", stripe_customer_id),
            ("stripe_subscription_id", stripe_subscription_id),
            ("current_period_start", current_period_start),
            ("current_period_end", current_period_end),
            ("cancel_at_period_end", cancel_at_period_end),
        ):
            if value is not None:
                record[field] = value
        record["updated_at"] = _now()
        return record

    async def find_tenant_by_stripe_customer(self, customer_id: str) -> str | None:
        for tenant_id, record in self.subscriptions.items():
            if record.get("stripe_customer_id") == customer_id:
                return tenant_id
        return None

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
        self, tenant_id: str, *, tenant_name: str, raw_key: str, label: str | None = None
    ) -> dict[str, Any]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        record = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "key_prefix": raw_key[:12],
            "label": label,
            "active": True,
            "revoked_at": None,
            "created_at": _now(),
            "last_used_at": None,
        }
        self.api_keys[key_hash] = record
        return record

    async def list_api_keys(self, tenant_id: str) -> list[dict[str, Any]]:
        # Hashen är dict-nyckeln och kommer aldrig med i utdatat.
        keys = [
            {
                "id": r["id"],
                "label": r.get("label"),
                "key_prefix": r["key_prefix"],
                "active": r["active"],
                "revoked_at": r.get("revoked_at"),
                "created_at": r["created_at"],
                "last_used_at": r.get("last_used_at"),
            }
            for r in self.api_keys.values()
            if r["tenant_id"] == tenant_id
        ]
        keys.sort(key=lambda k: k["created_at"], reverse=True)
        return keys

    async def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        for record in self.api_keys.values():
            if (
                record["id"] == key_id
                and record["tenant_id"] == tenant_id
                and not record.get("revoked_at")
            ):
                record["active"] = False
                record["revoked_at"] = _now()
                return True
        return False

    async def close(self) -> None:
        return None
