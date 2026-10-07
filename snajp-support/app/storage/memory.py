"""In-memory-lagring (multi-tenant) med samma gränssnitt som PostgresStorage.

Används när DATABASE_URL saknas eller databasen inte går att nå. All data
partitioneras per tenant: kunder, ärenden, kunskapsbas och API-nycklar är
helt isolerade mellan tenants, precis som RLS-policyerna i Postgres-läget.
Default-tenanten (Nordlys Handel) seedas med demo-kunskapsbasen.
"""

import hashlib
import json
import re
import unicodedata
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
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
from .base import (
    BEDOMNINGSFALT,
    AGENT_RUN_TYPES,
    ANALYTICS_COVERAGE,
    FEEDBACK_VERDICTS,
    LEADS_BUDGET_AGENT_TYPES,
    MEDDELANDE_AVSANDARE,
    SUPPORT_BUDGET_AGENT_TYPES,
    bk_belopp,
    bk_datum,
    kontrollera_bk_balans,
    normalisera_kunddata,
    kontrollera_bk_betalstatus,
    kontrollera_bk_granskningsstatus,
    kontrollera_bk_kalla,
    kontrollera_bk_riktning,
    kontrollera_bk_status,
    kontrollera_samtalslage,
    standard_samtalslage,
    status_transition_allowed,
)

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


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d is not None else None


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
        # Trial (074): kandidatrader sätts av tester, loggen speglar
        # trial_paminnelser-tabellen med (workspace_id, typ) som nyckel.
        self.trial_kandidater: list[dict[str, Any]] = []
        self.trial_paminnelser: dict[tuple[str, str], dict[str, Any]] = {}
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
        # tenant -> adress -> token. Speglar ss_avregistreringslankar.
        self.avregistreringslankar: dict[str, dict[str, str]] = {}
        self.outreach_threads: dict[str, dict[str, dict[str, Any]]] = {}
        self.outreach_messages: dict[str, list[dict[str, Any]]] = {}
        # Agentens föreslagna lärdomar (migration 051). Skrivs av support-
        # och leads-körningarna, godkänns av en människa (INV-LEARN-001).
        self.agent_suggestions: dict[str, list[dict[str, Any]]] = {}
        # Kundens dom över körningar (agent_feedback, migration 010 — första
        # kodvägen 2026-08-26).
        self.agent_feedback: dict[str, list[dict[str, Any]]] = {}
        # Kundminne (migration 052): (tenant_id, customer_id) -> faktarader.
        self.customer_memory: dict[tuple[str, str], list[dict[str, Any]]] = {}
        # Samtalsläge (migration 066): (tenant_id, customer_id) -> läget.
        self.chat_states: dict[tuple[str, str], dict[str, Any]] = {}
        # Golden eval-cases (agent_evals, migration 010 — första kodvägen
        # 2026-08-27).
        self.eval_cases: dict[str, list[dict[str, Any]]] = {}
        # G11: (tenant_id, segment, lever) -> {sent, replies, positive}. Seedas
        # direkt i tester — ingen API-yta skriver hit än (samma status som
        # send_queue/outreach_* ovan).
        self.ab_results: list[dict[str, Any]] = []
        self.prospects: dict[str, list[dict[str, Any]]] = {}
        self.prospect_sources: dict[str, list[dict[str, Any]]] = {}
        self.agent_runs: dict[str, list[dict[str, Any]]] = {}
        #: prompt_lager (migration 101): {hash: text}, global som tabellen.
        self.prompt_lager: dict[str, str] = {}
        # Leads-jobbens liggare (INV-JOB-002, migration 059). Nycklad på
        # job_id precis som Postgres-tabellens primärnyckel.
        self.leads_job_ledger: dict[str, dict[str, Any]] = {}
        # Leadslistor (tillägget 'leadlists', migration 060).
        self.lead_lists: dict[str, list[dict[str, Any]]] = {}
        #: Säljlistan (public.saljlista) som motorn fyller på (migration 105).
        self._saljlista: dict[str, list[dict[str, Any]]] = {}
        self.lead_list_items: list[dict[str, Any]] = []
        # Leads Suite (migration 086): platta listor, samma form som tabellerna.
        self.lead_anteckningar: list[dict[str, Any]] = []
        self.lead_uppgifter: list[dict[str, Any]] = []
        self.prospect_status_logg: list[dict[str, Any]] = []
        self.lead_vyer: list[dict[str, Any]] = []
        # Bokföring (migration 045). Filen sparas aldrig — bara sha256:n.
        self.bk_underlag: dict[str, list[dict[str, Any]]] = {}
        self.kvittomejl_lasta: dict[str, dict[str, str]] = {}
        self.bk_verifikat: dict[str, list[dict[str, Any]]] = {}
        # (scope_kind, scope_id, kind) -> tidsstämplar. Inte tenant-nycklad,
        # eftersom demons IP-scope inte har någon tenant (migration 019).
        self.rate_events: dict[tuple[str, str, str], list[datetime]] = {}
        # (tenant_id, agent_type) -> agent_configs.settings (migration 023)
        self.agent_settings: dict[tuple[str, str], dict[str, Any]] = {}
        # (tenant_id, agent_type) -> instructions_md/instructions_rav/tone
        # (migration 049). Skild från agent_settings av samma skäl som i
        # PostgresStorage: settings läses av varje leads-körning, det här
        # läses bara av admin och av promptbygget.
        self.agent_instructions: dict[tuple[str, str], dict[str, Any]] = {}
        # Plattformsövergripande instruktioner, nyast först. Lista och inte en
        # rad: historiken är hela poängen med att versionera dem.
        self.global_instructions: list[dict[str, Any]] = []
        # Plattformsnivå, inte tenant-nycklad: ett fel i proxyn eller i
        # schemaläggaren innan den vet vilken kund det gäller hör hemma här
        # också (migration 026, tenant_id nullable).
        self.platform_events: list[dict[str, Any]] = []
        # Kundregistret (migration 053): en detaljrad per tenant_id, och
        # kontaktpersoner som platt lista — samma form som Postgres-tabellerna.
        self.customer_details: dict[str, dict[str, Any]] = {}
        self.customer_contacts: list[dict[str, Any]] = []
        # Nycklad på manifest_hash, inte tenant_id — delad baselinekatalog
        # (migration 016). Samma undantag som segmentaggregatet.
        self.skill_files: dict[str, list[dict[str, Any]]] = {}

        # Email-pipeline
        # In-memory-läget har inga riktiga inkorgar — mock-mail matas in direkt
        # via /api/inbox. Dicten finns för att lagringsgränssnittet ska vara
        # detsamma i båda lägena.
        self.mailboxes: dict[str, dict[str, Any]] = {}
        self.flytt_ko: list[dict[str, Any]] = []  # dev_flytt_ko (085)
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
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            return None
        # Samma överlagring som Postgres-joinen mot ss_customer_details:
        # registrets avsändaruppgifter syns i tenant-dicten. Värden som redan
        # står på tenantposten vinner — testerna sätter dem ofta direkt där.
        detaljer = self.customer_details.get(tenant_id, {})
        overlagd = dict(tenant)
        for nyckel, falt in (
            ("orgnr", "orgnr"),
            ("postal_address", "foretagsadress"),
            ("policy_url", "policy_url"),
        ):
            if overlagd.get(nyckel) is None:
                overlagd[nyckel] = detaljer.get(falt)
        return overlagd

    async def set_tenant_active(self, tenant_id: str, *, active: bool) -> dict[str, Any] | None:
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            return None
        tenant["active"] = active
        # Speglar Postgres (080): spärren och etiketten skrivs tillsammans.
        tenant["status"] = "aktiv" if active else "avstangd"
        return dict(tenant)

    async def set_tenant_status(self, tenant_id: str, *, status: str) -> dict[str, Any] | None:
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            return None
        tenant["status"] = status
        tenant["active"] = status == "aktiv"
        return dict(tenant)

    async def get_tenant_products(self, tenant_id: str) -> list[str] | None:
        # Minnet har inga arbetsytor — tester sätter `products` direkt på
        # tenantposten, samma nyckel som list_tenants_with_stats speglar.
        return (self.tenants.get(tenant_id) or {}).get("products")

    async def list_tenants(self) -> list[dict[str, Any]]:
        return [t for t in self.tenants.values() if t.get("active", True)]

    # -- Inkorgar -----------------------------------------------------------

    async def spegel_info(self) -> dict[str, Any] | None:
        return None  # minneslagret speglas aldrig

    async def logga_flytt(self, tenant_id: str, *, typ: str, ref_id: str, resultat: str) -> None:
        if typ not in ("mejl", "korning"):
            raise ValueError(f"typ={typ!r} bryter mot dev_flytt_ko-checken (085).")
        self.flytt_ko.append({
            "id": str(uuid.uuid4()), "tenant_id": tenant_id, "typ": typ, "ref_id": ref_id,
            "skapad_at": _now(), "flyttad_at": _now() if resultat == "ok" else None, "resultat": resultat,
        })

    async def list_flytt(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        rader = [r for r in self.flytt_ko if r["tenant_id"] == tenant_id]
        rader.sort(key=lambda r: r["skapad_at"], reverse=True)
        return [dict(r) for r in rader[:limit]]

    async def list_mailboxes(self, tenant_id: str) -> list[dict[str, Any]]:
        return [m for m in self.mailboxes.values() if m["tenant_id"] == tenant_id]

    async def upsert_mailbox(
        self,
        tenant_id: str,
        *,
        provider: str,
        address: str,
        imap_host: str | None = None,
        secret_enc: str | None = None,
        syfte: str = "support",
    ) -> dict[str, Any]:
        adress = address.strip().lower()
        if syfte not in ("support", "leads", "bada"):
            raise ValueError(f"syfte={syfte!r} bryter mot ss_mailboxes-checken (084).")
        for rad in self.mailboxes.values():
            if rad["tenant_id"] == tenant_id and rad["address"] == adress:
                rad.update(
                    provider=provider,
                    imap_host=imap_host,
                    secret_enc=secret_enc,
                    status="active",
                    last_error=None,
                    syfte=syfte,
                )
                return rad
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "provider": provider,
            "address": adress,
            "status": "active",
            "imap_host": imap_host,
            "secret_enc": secret_enc,
            "syfte": syfte,
            "last_sync_at": None,
            "last_error": None,
            "created_at": _now(),
        }
        self.mailboxes[rad["id"]] = rad
        return rad

    async def delete_mailbox(self, tenant_id: str, mailbox_id: str) -> bool:
        rad = self.mailboxes.get(mailbox_id)
        if rad and rad["tenant_id"] == tenant_id:
            del self.mailboxes[mailbox_id]
            return True
        return False

    async def touch_mailbox_sync(
        self, tenant_id: str, mailbox_id: str, *, last_error: str | None
    ) -> None:
        rad = self.mailboxes.get(mailbox_id)
        if rad and rad["tenant_id"] == tenant_id:
            rad["last_sync_at"] = _now()
            rad["last_error"] = last_error

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
        is_test: bool = False,
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
            "is_test": is_test,
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
        is_test: bool | None = None,
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
        if is_test is not None:
            ticket["is_test"] = is_test
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
        author: str | None = None,
    ) -> dict[str, Any]:
        conversation = self.conversations.get(conversation_id)
        if not conversation or conversation["tenant_id"] != tenant_id:
            raise ValueError("Konversationen tillhör inte denna tenant.")
        if author is not None and author not in MEDDELANDE_AVSANDARE:
            # Samma villkor som ss_messages_author_check i migration 066.
            raise ValueError(f"Okänd avsändare: {author!r}")
        message = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "direction": direction,
            "content": content,
            "sentiment": sentiment,
            "has_image": has_image,
            "author": author,
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

    async def find_customer(self, tenant_id: str, *, email: str) -> dict[str, Any] | None:
        if not email:
            return None
        customer_id = self.identifiers.get((tenant_id, "email", email.lower()))
        return self.customers.get(customer_id) if customer_id else None

    async def list_trial_paminnelse_kandidater(self, *, idag: date) -> list[dict[str, Any]]:
        # Minnet har inga arbetsytor — tester fyller `self.trial_kandidater`
        # med färdiga rader (samma fält som Postgres-frågan returnerar) och
        # den här metoden filtrerar bara bort redan loggade påminnelser,
        # så att svepar-logiken kan mätas utan databas.
        rader = []
        for rad in getattr(self, "trial_kandidater", []):
            typ = "7_dagar" if rad.get("dagar_kvar") == 7 else "1_dag"
            if (rad["workspace_id"], typ) not in self.trial_paminnelser:
                rader.append(dict(rad))
        return rader

    async def spara_trial_paminnelse(
        self, *, workspace_id: str, typ: str, skickad_till: str
    ) -> bool:
        if (workspace_id, typ) in self.trial_paminnelser:
            return False
        self.trial_paminnelser[(workspace_id, typ)] = {
            "workspace_id": workspace_id,
            "typ": typ,
            "skickad_till": skickad_till,
            "created_at": _now(),
        }
        return True

    async def list_customer_emails(self, tenant_id: str) -> list[str]:
        return sorted(
            varde
            for (tid, typ, varde) in self.identifiers
            if tid == tenant_id and typ == "email"
        )

    # -- Samtalsläge (migration 066) ----------------------------------------

    async def get_chat_state(self, tenant_id: str, customer_id: str) -> dict[str, Any]:
        rad = self.chat_states.get((tenant_id, customer_id))
        return dict(rad) if rad else standard_samtalslage(tenant_id, customer_id)

    async def save_chat_state(
        self,
        tenant_id: str,
        customer_id: str,
        *,
        lage: str,
        misslyckade_i_rad: int,
        erbjod_manniska: bool,
        overlamnad_orsak: str | None = None,
        overlamnad_ticket_id: str | None = None,
        sprak: str | None = None,
    ) -> dict[str, Any]:
        kontrollera_samtalslage(lage, misslyckade_i_rad)
        tidigare = self.chat_states.get((tenant_id, customer_id))
        nu = _now()
        if lage == "overlamnad":
            overlamnad_at = (
                tidigare["overlamnad_at"]
                if tidigare and tidigare["lage"] == "overlamnad" and tidigare["overlamnad_at"]
                else nu
            )
        else:
            overlamnad_at = None
        rad = {
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "lage": lage,
            "misslyckade_i_rad": misslyckade_i_rad,
            "erbjod_manniska": erbjod_manniska,
            "overlamnad_orsak": overlamnad_orsak,
            "overlamnad_ticket_id": overlamnad_ticket_id,
            "overlamnad_at": overlamnad_at,
            "sprak": sprak,
            "updated_at": nu,
        }
        self.chat_states[(tenant_id, customer_id)] = rad
        return dict(rad)

    async def list_chat_handovers(
        self, tenant_id: str, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        rader = []
        for (tid, customer_id), rad in self.chat_states.items():
            if tid != tenant_id or rad["lage"] != "overlamnad":
                continue
            kund = self.customers.get(customer_id) or {}
            arende = self.tickets.get(rad.get("overlamnad_ticket_id") or "") or {}
            rader.append(
                {
                    **rad,
                    "customer_name": kund.get("name"),
                    "subject": arende.get("subject"),
                    "category": arende.get("category"),
                    # Kanalerna (bd snipe-36u): Chattar-vyn visar var kunden
                    # sitter, och att ett svar måste SKICKAS dit.
                    "channel": arende.get("channel"),
                    "is_test": bool(arende.get("is_test")),
                }
            )
        rader.sort(key=lambda r: r["updated_at"], reverse=True)
        return rader[:limit]

    # -- Kunskapsbas --------------------------------------------------------

    async def search_kb(
        self,
        tenant_id: str,
        query: str,
        embedding: list[float] | None = None,
        # 3, inte 5. Protokollet och PostgresStorage sa 3; bara minnet sa 5,
        # och alla åtta anropare använder default-värdet. Följden var att varje
        # test matade agenten med FEM artiklar där produktionen ger TRE — en
        # skillnad i vad modellen faktiskt läser, osynlig i båda filerna var
        # för sig. Hittad av tests/invariants/test_inv_store_001.py.
        limit: int = 3,
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
        row["embedding"] = embedding
        self.kb.setdefault(tenant_id, []).append(row)
        return {"id": row["id"], "title": title, "category": category}

    async def delete_kb_article(self, tenant_id: str, artikel_id: str) -> bool:
        artiklar = self.kb.get(tenant_id, [])
        kvar = [a for a in artiklar if str(a["id"]) != str(artikel_id)]
        self.kb[tenant_id] = kvar
        return len(kvar) < len(artiklar)

    async def kb_utan_vektor(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {"id": a["id"], "title": a["title"], "content": a["content"]}
            for a in self.kb.get(tenant_id, []) if a.get("embedding") is None
        ][:limit]

    async def satt_kb_vektor(self, tenant_id: str, artikel_id: str, embedding: list[float]) -> None:
        for a in self.kb.get(tenant_id, []):
            if str(a["id"]) == str(artikel_id):
                a["embedding"] = embedding

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
        # Versionen bryter lika tidsstämplar: två sparningar inom samma
        # klockslag (Windows upplösning ~15 ms) ska ändå ge nyast först.
        return sorted(docs, key=lambda d: (d["created_at"], d.get("version") or 0), reverse=True)

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
        thread = self.outreach_threads.get(tenant_id, {}).get(thread_id)
        if thread is None:
            return None
        # Speglar SQL-joinens prospect_email/company_name. Utan dem var
        # minnesvarianten en lögn om vad produktionen returnerar — och
        # svarshanteringens suppressions-väg blev tyst tom i test medan den
        # fungerade mot Postgres (upptäckt 2026-08-26, exakt den divergens
        # kommentaren nedan varnar för).
        prospekt = next(
            (p for p in self.prospects.get(tenant_id, []) if p["id"] == thread.get("prospect_id")),
            None,
        )
        # Prospektets värden när prospektet finns (joinens semantik); annars
        # behålls det tråden själv bär — fixturer seedar fälten direkt på
        # tråddicten, och en LEFT JOIN skriver inte över med NULL.
        berikad = dict(thread)
        if prospekt:
            berikad["prospect_email"] = prospekt.get("contact_email")
            berikad["company_name"] = prospekt.get("company_name")
        else:
            berikad.setdefault("prospect_email", None)
            berikad.setdefault("company_name", None)
        return berikad

    # -- Underlaget send_guard dömer på (DEL 2.3) ---------------------------
    # Samma signaturer och samma normalisering som PostgresStorage. Skiljer de
    # sig åt är minnesvägen en lögn om vad produktionen gör.

    async def list_suppressions(self, tenant_id: str) -> set[str]:
        return {
            str(rad["email"]).strip().casefold()
            for rad in self.suppressions.get(tenant_id, [])
        }

    async def avregistreringstoken(self, tenant_id: str, *, email: str) -> str:
        adress = str(email or "").strip().casefold()
        if not adress:
            raise ValueError("avregistreringstoken kräver en e-postadress.")
        from ..leads.utskicksfot import ny_token

        lankar = self.avregistreringslankar.setdefault(tenant_id, {})
        if adress not in lankar:
            lankar[adress] = ny_token()
        return lankar[adress]

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

    async def get_send_queue_item(self, tenant_id: str, item_id: str) -> dict[str, Any] | None:
        for item in self.send_queue.get(tenant_id, []):
            if item["id"] == item_id:
                return item
        return None

    async def senaste_ko_for_trad(self, tenant_id: str, thread_id: str) -> dict[str, Any] | None:
        poster = [i for i in self.send_queue.get(tenant_id, []) if i["thread_id"] == thread_id]
        return poster[-1] if poster else None

    async def update_outreach_message_text(
        self, tenant_id: str, message_id: str, *, subject: str, body: str
    ) -> None:
        for message in self.outreach_messages.get(tenant_id, []):
            if message["id"] == message_id and message["sent_at"] is None:
                message["subject"] = subject
                message["body"] = body
                return

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

    async def find_outreach_thread(
        self, tenant_id: str, *, prospect_id: str
    ) -> dict[str, Any] | None:
        # Läsdelen av ensure_outreach_thread — se base.py: en GET får inte
        # lämna en tom tråd efter sig.
        for thread in self.outreach_threads.get(tenant_id, {}).values():
            if thread.get("prospect_id") == prospect_id:
                return thread
        return None

    async def ensure_outreach_thread(
        self, tenant_id: str, *, prospect_id: str
    ) -> dict[str, Any]:
        trådar = self.outreach_threads.setdefault(tenant_id, {})
        for thread in trådar.values():
            if thread.get("prospect_id") == prospect_id:
                return thread
        thread = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "prospect_id": prospect_id,
            "offer_id": None,
            "language_state": "sv",
            "last_inbound_at": None,
            "created_at": _now(),
        }
        trådar[thread["id"]] = thread
        return thread

    async def record_inbound_reply(
        self, tenant_id: str, *, thread_id: str, body: str
    ) -> dict[str, Any]:
        thread = self.outreach_threads.get(tenant_id, {}).get(thread_id)
        if thread is None:
            raise ValueError(f"Tråden {thread_id} finns inte hos tenanten.")
        message = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "thread_id": thread_id,
            "direction": "inbound",
            "body": body,
            "subject": None,
            "humanizer_variant": None,
            # Speglar SQL-varianten: inbound-radens sent_at är mottagandetiden.
            # list_replies sorterar på den, och en NULL hade sorterat svaret sist.
            "sent_at": _now(),
        }
        self.outreach_messages.setdefault(tenant_id, []).append(message)
        thread["last_inbound_at"] = message["sent_at"]
        return message

    async def list_outreach_threads(self, tenant_id: str) -> list[dict[str, Any]]:
        prospekt = {p["id"]: p for p in self.prospects.get(tenant_id, [])}
        meddelanden = self.outreach_messages.get(tenant_id, [])
        kö = self.send_queue.get(tenant_id, [])

        resultat = []
        for thread in self.outreach_threads.get(tenant_id, {}).values():
            tid = thread["id"]
            utgående = [
                m for m in meddelanden if m["thread_id"] == tid and m["direction"] == "outbound"
            ]
            skickade = [m for m in utgående if m.get("sent_at")]
            p = prospekt.get(thread.get("prospect_id")) or {}
            resultat.append(
                {
                    **thread,
                    "company_name": p.get("company_name"),
                    "contact_email": p.get("contact_email"),
                    "origin": p.get("origin"),
                    "outbound_sent_count": len(skickade),
                    "last_outbound_sent_at": max((m["sent_at"] for m in skickade), default=None),
                    # Osänt utkast ELLER aktiv köpost räknas — båda betyder att
                    # tråden redan har ett nästa steg och inte ska få ett till.
                    "has_pending_item": bool(
                        [m for m in utgående if not m.get("sent_at")]
                        or [
                            q
                            for q in kö
                            if q["thread_id"] == tid
                            and q["status"] in ("queued", "awaiting_review")
                        ]
                    ),
                }
            )
        return resultat

    async def cancel_pending_sends(self, tenant_id: str, thread_id: str) -> int:
        antal = 0
        for item in self.send_queue.get(tenant_id, []):
            if item["thread_id"] == thread_id and item["status"] in ("queued", "awaiting_review"):
                item["status"] = "cancelled"
                antal += 1
        return antal

    async def reschedule_pending_sends(
        self, tenant_id: str, thread_id: str, *, until: Any
    ) -> int:
        antal = 0
        for item in self.send_queue.get(tenant_id, []):
            if item["thread_id"] == thread_id and item["status"] == "queued":
                item["scheduled_at"] = until
                antal += 1
        return antal

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
        rader = self.agent_suggestions.setdefault(tenant_id, [])
        if any(r["dedupe_key"] == dedupe_key and r["status"] == "ny" for r in rader):
            return None
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "agent_type": agent_type,
            "kind": kind,
            "title": title,
            "content": content,
            "dedupe_key": dedupe_key,
            "status": "ny",
            "created_at": _now(),
        }
        rader.append(rad)
        return rad

    async def list_agent_suggestions(
        self, tenant_id: str, *, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        rader = [
            r
            for r in self.agent_suggestions.get(tenant_id, [])
            if status is None or r["status"] == status
        ]
        rader.sort(key=lambda r: r["created_at"], reverse=True)
        return rader[:limit]

    async def update_agent_suggestion_status(
        self, tenant_id: str, suggestion_id: str, *, status: str
    ) -> dict[str, Any] | None:
        for rad in self.agent_suggestions.get(tenant_id, []):
            if rad["id"] == suggestion_id:
                rad["status"] = status
                return rad
        return None

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
        if verdict not in FEEDBACK_VERDICTS:
            raise ValueError(
                f"verdict={verdict!r} finns inte i agent_feedback-checken "
                f"{FEEDBACK_VERDICTS}. Mot Postgres hade det kastat check-violation."
            )
        # Speglar FK:n mot agent_runs. Utan raden tar minnet emot ett run_id
        # som inte finns medan Postgres kastar — dagens läxa, igen.
        if not any(r["id"] == run_id for r in self.agent_runs.get(tenant_id, [])):
            raise ValueError(f"run_id={run_id!r} finns inte i agent_runs hos tenanten.")
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "run_id": run_id,
            "verdict": verdict,
            "comment": comment,
            "corrected_output": corrected_output,
            "created_at": _now(),
        }
        self.agent_feedback.setdefault(tenant_id, []).append(rad)
        return rad

    async def list_agent_feedback(
        self, tenant_id: str, *, verdict: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        # Baklänges FÖRE sorteringen: två domar inom samma klocktick får
        # identisk created_at (Windows-klockan tickar grovt), och en stabil
        # sort behåller då ordningen den fick — alltså äldst först. Med listan
        # reverserad blir det bevarade läget i stället senast insatt först,
        # vilket är vad "senast först" faktiskt lovar.
        rader = [
            r
            for r in reversed(self.agent_feedback.get(tenant_id, []))
            if verdict is None or r["verdict"] == verdict
        ]
        rader.sort(key=lambda r: r["created_at"], reverse=True)
        return rader[:limit]

    # -- Kundminne (migration 052) ------------------------------------------

    async def add_customer_facts(
        self, tenant_id: str, customer_id: str, *, fakta: list[str]
    ) -> int:
        rader = self.customer_memory.setdefault((tenant_id, customer_id), [])
        kanda = {r["fakta"].strip().casefold() for r in rader}
        antal = 0
        for rad in fakta:
            text = str(rad or "").strip()
            if not text or text.casefold() in kanda:
                continue
            rader.append({"fakta": text, "created_at": _now()})
            kanda.add(text.casefold())
            antal += 1
        return antal

    async def get_customer_facts(
        self, tenant_id: str, customer_id: str, *, limit: int = 12
    ) -> list[str]:
        rader = self.customer_memory.get((tenant_id, customer_id), [])
        # Senaste `limit`, men i kronologisk läsordning för prompten.
        return [r["fakta"] for r in rader[-max(1, limit):]]

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
        if agent_type not in ("support", "leads"):
            raise ValueError(
                f"agent_type={agent_type!r} finns inte i agent_evals-checken. "
                "Mot Postgres hade det kastat check-violation."
            )
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "agent_type": agent_type,
            "input": input_text,
            # Kolumnen är text (migration 010) — JSON serialiseras vid
            # skrivning i BÅDA lagringarna så läsaren alltid får en dict.
            "expected_traits": json.dumps(expected_traits, ensure_ascii=False),
            "approved_output": approved_output,
            "created_at": _now(),
        }
        self.eval_cases.setdefault(tenant_id, []).append(rad)
        return {**rad, "expected_traits": expected_traits}

    async def list_eval_cases(
        self, tenant_id: str, *, agent_type: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        rader = [
            {**r, "expected_traits": json.loads(r["expected_traits"])}
            for r in self.eval_cases.get(tenant_id, [])
            if agent_type is None or r["agent_type"] == agent_type
        ]
        return rader[:limit]

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
                if namn
                in (
                    "orgnr",
                    "ort",
                    "postnr",
                    "sni",
                    "website",
                    "anstallda",
                    "omsattning",
                    "contact_role",
                    "contact_level",
                    "contact_form_url",
                    "contact_phone",
                    "importerad_fran",
                )
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
        origin: str | None = None,
        orgnr: str | None = None,
        website: str | None = None,
        contact_email: str | None = None,
        contact_name: str | None = None,
        contact_role: str | None = None,
        contact_level: str | None = None,
        contact_form_url: str | None = None,
        status_kalla: str = "kod",
    ) -> dict[str, Any] | None:
        prospect = await self.get_prospect(tenant_id, prospect_id)
        if not prospect:
            return None
        if status is not None and status != prospect.get("status"):
            if status_kalla not in ("kod", "manuell", "import"):
                raise ValueError(f"status_kalla={status_kalla!r} bryter mot checken (086).")
            self.prospect_status_logg.append(
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "prospect_id": prospect_id,
                    "fran": prospect.get("status"),
                    "till": status,
                    "kalla": status_kalla,
                    "created_at": _now(),
                }
            )
        for field, value in (
            ("status", status),
            ("icp_fit", icp_fit),
            ("qualified", qualified),
            ("disqualifiers", disqualifiers),
            ("origin", origin),
            ("orgnr", orgnr),
            ("website", website),
            ("contact_email", contact_email),
            ("contact_name", contact_name),
            ("contact_role", contact_role),
            ("contact_level", contact_level),
            ("contact_form_url", contact_form_url),
        ):
            if value is not None:
                prospect[field] = value
        return prospect

    # -- Leads Suite (migration 086) -----------------------------------------

    def _ager_prospekt(self, tenant_id: str, prospect_id: str) -> None:
        # Speglar FK + RLS: Postgres fäller en rad mot ett prospekt som inte
        # finns hos tenanten, så minnet ska också göra det.
        if not any(p["id"] == prospect_id for p in self.prospects.get(tenant_id, [])):
            raise ValueError(f"Prospektet {prospect_id} finns inte hos tenanten.")

    @staticmethod
    def _nyast_forst(rader: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # reversed först: lika tidsstämplar ska också ge den senast skrivna först.
        return [dict(r) for r in sorted(reversed(rader), key=lambda r: r["created_at"], reverse=True)]

    async def add_lead_note(self, tenant_id: str, *, prospect_id: str, text: str) -> dict[str, Any]:
        self._ager_prospekt(tenant_id, prospect_id)
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "prospect_id": prospect_id,
            "text": text,
            "created_at": _now(),
        }
        self.lead_anteckningar.append(rad)
        return dict(rad)

    async def list_lead_notes(self, tenant_id: str, prospect_id: str) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self.lead_anteckningar
            if r["tenant_id"] == tenant_id and r["prospect_id"] == prospect_id
        ]

    async def add_lead_task(
        self, tenant_id: str, *, prospect_id: str, titel: str, forfaller: str | None
    ) -> dict[str, Any]:
        self._ager_prospekt(tenant_id, prospect_id)
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "prospect_id": prospect_id,
            "titel": titel,
            # Samma form som Postgres-vägen: date → ISO-sträng.
            "forfaller": date.fromisoformat(forfaller).isoformat() if forfaller else None,
            "klar": False,
            "klar_at": None,
            "created_at": _now(),
        }
        self.lead_uppgifter.append(rad)
        return dict(rad)

    async def update_lead_task(
        self, tenant_id: str, task_id: str, *, klar: bool | None = None
    ) -> dict[str, Any] | None:
        for rad in self.lead_uppgifter:
            if rad["id"] == task_id and rad["tenant_id"] == tenant_id:
                if klar is not None and klar != rad["klar"]:
                    rad["klar"] = klar
                    rad["klar_at"] = _now() if klar else None
                return dict(rad)
        return None

    async def list_lead_tasks(
        self, tenant_id: str, *, prospect_id: str | None = None, bara_oppna: bool = False
    ) -> list[dict[str, Any]]:
        rader = [
            r
            for r in self.lead_uppgifter
            if r["tenant_id"] == tenant_id
            and (prospect_id is None or r["prospect_id"] == prospect_id)
            and not (bara_oppna and r["klar"])
        ]
        rader.sort(key=lambda r: (r["forfaller"] is None, r["forfaller"] or "", r["created_at"]))
        return [dict(r) for r in rader]

    async def list_status_logg(
        self, tenant_id: str, *, prospect_id: str | None = None
    ) -> list[dict[str, Any]]:
        return self._nyast_forst(
            [
                r
                for r in self.prospect_status_logg
                if r["tenant_id"] == tenant_id and (prospect_id is None or r["prospect_id"] == prospect_id)
            ]
        )

    async def list_lead_views(self, tenant_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self.lead_vyer if r["tenant_id"] == tenant_id]

    async def create_lead_view(
        self, tenant_id: str, *, namn: str, filter: dict[str, Any]
    ) -> dict[str, Any]:
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "namn": namn,
            "filter": json.loads(json.dumps(filter)),
            "created_at": _now(),
        }
        self.lead_vyer.append(rad)
        return dict(rad)

    async def delete_lead_view(self, tenant_id: str, view_id: str) -> bool:
        fore = len(self.lead_vyer)
        self.lead_vyer = [
            r for r in self.lead_vyer if not (r["id"] == view_id and r["tenant_id"] == tenant_id)
        ]
        return len(self.lead_vyer) < fore

    async def spara_bedomning(
        self, tenant_id: str, prospect_id: str, *, bedomning: dict[str, Any]
    ) -> dict[str, Any] | None:
        prospect = await self.get_prospect(tenant_id, prospect_id)
        if not prospect:
            return None
        for falt in BEDOMNINGSFALT:
            if bedomning.get(falt) is not None:
                prospect[falt] = bedomning[falt]
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
        # Migration 055. Se base.py:s docstring för värdemängden.
        model: str | None = None,
        prompt_lager: dict[str, str] | None = None,
        prospect_id: str | None = None,
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
            "model": model,
            "pack_version": pack_version,
            "skills_used": skills_used,
            "input": input_text,
            "output": output_text,
            "step_log": step_log,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "prospect_id": prospect_id,
            "created_at": _now(),
        }
        self.agent_runs.setdefault(tenant_id, []).append(run)
        # on conflict do nothing: första texten per hash står kvar.
        for hash_, text in (prompt_lager or {}).items():
            self.prompt_lager.setdefault(hash_, text)
        return run

    async def get_prompt_lager(self, hashar: list[str]) -> dict[str, str]:
        return {h: self.prompt_lager[h] for h in hashar if h in self.prompt_lager}

    async def list_agent_runs(
        self, tenant_id: str, *, agent_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        runs = self.agent_runs.get(tenant_id, [])
        if agent_type:
            runs = [r for r in runs if r["agent_type"] == agent_type]
        return sorted(runs, key=lambda r: r["created_at"], reverse=True)[:limit]

    # -- Leads-jobbens liggare (INV-JOB-002, migration 059) -----------------

    async def set_leads_job_status(
        self,
        tenant_id: str,
        *,
        job_id: str,
        status: str,
        scope: str = "research",
        prospect_id: str | None = None,
        korning: dict[str, Any] | None = None,
        error: str | None = None,
        is_test: bool | None = None,
    ) -> None:
        # Samma värdemängd som check-villkoret i migration 059 — minnet ska
        # kasta där Postgres kastar (samma regel som AGENT_RUN_TYPES ovan).
        if status not in ("queued", "processing", "completed", "failed"):
            raise ValueError(f"status={status!r} bryter mot leads_job_ledger-checken.")
        rad = self.leads_job_ledger.setdefault(
            job_id,
            {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "prospect_id": prospect_id,
                "scope": scope,
                "created_at": _now(),
                "completed_at": None,
                "korning": None,
                "error": None,
                "is_test": False,
            },
        )
        rad["status"] = status
        rad["updated_at"] = _now()
        if status in ("completed", "failed"):
            rad["completed_at"] = _now()
        # Djupkopia: motorn muterar sitt dict efter skrivningen, och
        # liggaren ska visa det som skrevs — samma semantik som jsonb.
        if korning is not None:
            ny = {k: v for k, v in json.loads(json.dumps(korning)).items() if k != "styrning"}
            if "styrning" in (rad["korning"] or {}):
                ny["styrning"] = rad["korning"]["styrning"]
            rad["korning"] = ny
        if error is not None:
            rad["error"] = error
        if is_test is not None:
            rad["is_test"] = is_test

    async def get_leads_job_status(self, tenant_id: str, job_id: str) -> str | None:
        rad = self.leads_job_ledger.get(job_id)
        if not rad or rad["tenant_id"] != tenant_id:
            return None
        return rad["status"]

    _KORNINGSFALT = ("job_id", "status", "scope", "is_test", "created_at", "updated_at",
                     "completed_at", "error", "korning")

    def _korningsrad(self, rad: dict[str, Any]) -> dict[str, Any]:
        return {f: rad.get(f) for f in self._KORNINGSFALT}

    async def list_prospekt_i_research(self, tenant_id: str) -> set[str]:
        return {
            str(r["prospect_id"])
            for r in self.leads_job_ledger.values()
            if r["tenant_id"] == tenant_id
            and r.get("prospect_id")
            and r["status"] in ("queued", "processing")
            and r["scope"] in ("research", "research_and_draft")
        }

    async def list_leads_korningar(self, tenant_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        rader = [
            r for r in self.leads_job_ledger.values()
            if r["tenant_id"] == tenant_id and r["scope"] in ("batch", "lista")
        ]
        # Senast insatta först INNAN sorteringen: sort() är stabil, så två
        # jobb med samma created_at (snabb maskin, samma millisekund) behåller
        # annars äldst-först-ordningen och bryter "nyast först"-kontraktet.
        rader.reverse()
        rader.sort(key=lambda r: r["created_at"], reverse=True)
        return [self._korningsrad(r) for r in rader[:limit]]

    async def get_sidcache(self, tenant_id: str, url: str) -> dict[str, Any] | None:
        rad = self.__dict__.setdefault("sidcache", {}).get((tenant_id, url))
        return dict(rad) if rad else None

    async def put_sidcache(self, tenant_id: str, url: str, *, innehall: str | None, fel: str | None) -> None:
        self.__dict__.setdefault("sidcache", {})[(tenant_id, url)] = {
            "innehall": innehall, "fel": fel, "hamtad_at": datetime.now(timezone.utc),
        }

    async def set_korning_styrning(self, tenant_id: str, job_id: str, styrning: str | None) -> bool:
        rad = self.leads_job_ledger.get(job_id)
        if (not rad or rad["tenant_id"] != tenant_id or rad["scope"] != "batch"
                or rad["status"] != "processing" or not rad["korning"] or rad["korning"].get("klar")):
            return False
        rad["korning"]["styrning"] = styrning
        rad["updated_at"] = _now()
        return True

    async def get_leads_korning(self, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        rad = self.leads_job_ledger.get(job_id)
        if not rad or rad["tenant_id"] != tenant_id or rad["scope"] not in ("batch", "lista"):
            return None
        return self._korningsrad(rad)

    # -- Leadslistor (tillägget 'leadlists', migration 060) -----------------

    _LEAD_LIST_STATUSAR = ("bestalld", "byggs", "klar", "fel")
    _LEAD_ITEM_TYPER = ("bolag", "privatperson")

    _LEAD_LIST_KALLOR = ("sok", "kombinerad", "import", "crm", "saljlista")
    _KONTAKTFILTER = ("alla", "telefon", "mejl", "bada")

    async def create_lead_list(
        self,
        tenant_id: str,
        *,
        titel: str,
        icp: dict[str, Any],
        antal: int,
        is_test: bool = False,
        kalla: str = "sok",
        kallistor: list[str] | None = None,
        kontaktfilter: str | None = None,
    ) -> dict[str, Any]:
        if not 1 <= antal <= 200:
            raise ValueError(f"antal={antal} bryter mot lead_lists-checken (1–200).")
        if kalla not in self._LEAD_LIST_KALLOR:
            raise ValueError(f"kalla={kalla!r} bryter mot lead_lists-checken (082).")
        if kontaktfilter is not None and kontaktfilter not in self._KONTAKTFILTER:
            raise ValueError(f"kontaktfilter={kontaktfilter!r} bryter mot lead_lists-checken (082).")
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "titel": titel,
            "icp": icp,
            "antal": antal,
            "status": "bestalld",
            "felorsak": None,
            "is_test": is_test,
            "kalla": kalla,
            "kallistor": list(kallistor) if kallistor else None,
            "kontaktfilter": kontaktfilter,
            "created_at": _now(),
            "completed_at": None,
        }
        self.lead_lists.setdefault(tenant_id, []).append(rad)
        return dict(rad)


    async def saljlista_fyll_pa(self, tenant_id: str, rader: list[dict[str, Any]]) -> int:
        """Minnesformen av 105:ans SQL-funktion: samma dedupnycklar
        (orgnr-siffror eller gement bolagsnamn), samma fält."""
        lista = self._saljlista.setdefault(tenant_id, [])

        def _siffror(v: Any) -> str:
            return "".join(c for c in str(v or "") if c.isdigit())

        n = 0
        for rad in rader:
            namn = str(rad.get("foretagsnamn") or "").strip()
            if not namn:
                continue
            orgnr = _siffror(rad.get("orgnr"))
            if any(
                (orgnr and _siffror(r.get("orgnr")) == orgnr)
                or r.get("foretagsnamn", "").casefold() == namn.casefold()
                for r in lista
            ):
                continue
            lista.append(
                {
                    "foretagsnamn": namn,
                    "orgnr": str(rad.get("orgnr") or ""),
                    "kontaktperson": str(rad.get("kontaktperson") or ""),
                    "kontaktnummer": str(rad.get("kontaktnummer") or ""),
                    "kontaktmail": str(rad.get("kontaktmail") or ""),
                    "anteckningar": str(rad.get("anteckningar") or ""),
                }
            )
            n += 1
        return n

    async def set_lead_list_status(
        self, tenant_id: str, list_id: str, *, status: str, felorsak: str | None = None
    ) -> None:
        if status not in self._LEAD_LIST_STATUSAR:
            raise ValueError(f"status={status!r} bryter mot lead_lists-checken.")
        for rad in self.lead_lists.get(tenant_id, []):
            if rad["id"] == list_id:
                rad["status"] = status
                rad["felorsak"] = felorsak
                if status in ("klar", "fel"):
                    rad["completed_at"] = _now()
                return

    async def list_lead_lists(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        rader = sorted(
            self.lead_lists.get(tenant_id, []), key=lambda r: r["created_at"], reverse=True
        )[:limit]
        return [
            {**r, "item_count": sum(1 for i in self.lead_list_items if i["list_id"] == r["id"])}
            for r in rader
        ]

    async def get_lead_list(self, tenant_id: str, list_id: str) -> dict[str, Any] | None:
        for rad in self.lead_lists.get(tenant_id, []):
            if rad["id"] == list_id:
                return dict(rad)
        return None

    async def add_lead_list_item(
        self, tenant_id: str, *, list_id: str, **falt: Any
    ) -> dict[str, Any]:
        item_typ = falt.get("item_typ") or "bolag"
        if item_typ not in self._LEAD_ITEM_TYPER:
            raise ValueError(f"item_typ={item_typ!r} bryter mot lead_list_items-checken.")
        rad = {
            "id": str(uuid.uuid4()),
            "list_id": list_id,
            "tenant_id": tenant_id,
            "item_typ": item_typ,
            "company_name": falt.get("company_name") or "",
            "website": falt.get("website"),
            "ort": falt.get("ort"),
            "contact_name": falt.get("contact_name"),
            "contact_role": falt.get("contact_role"),
            "contact_email": falt.get("contact_email"),
            "contact_level": falt.get("contact_level"),
            "source_name": falt.get("source_name"),
            "source_url": falt.get("source_url"),
            "signal": falt.get("signal"),
            "signal_detalj": falt.get("signal_detalj"),
            "contact_phone": falt.get("contact_phone"),
            "orgnr": falt.get("orgnr"),
            "created_at": _now(),
        }
        self.lead_list_items.append(rad)
        return dict(rad)

    async def list_lead_list_items(self, tenant_id: str, list_id: str) -> list[dict[str, Any]]:
        return [
            dict(i)
            for i in self.lead_list_items
            if i["list_id"] == list_id and i["tenant_id"] == tenant_id
        ]

    async def spara_listutkast(
        self, tenant_id: str, item_id: str, utkast: dict[str, Any] | None
    ) -> None:
        for i in self.lead_list_items:
            if str(i["id"]) == str(item_id) and i["tenant_id"] == tenant_id:
                i["utkast"] = json.loads(json.dumps(utkast)) if utkast is not None else None

    async def lista_upptagna_bolag(self, tenant_id: str) -> list[dict[str, Any]]:
        rader = [*self.prospects.get(tenant_id, []), *(i for i in self.lead_list_items if i["tenant_id"] == tenant_id)]
        return [{"company_name": r.get("company_name"), "orgnr": r.get("orgnr")} for r in rader]

    async def rensa_lead_list_items(self, tenant_id: str, list_id: str) -> int:
        fore = len(self.lead_list_items)
        self.lead_list_items = [
            i
            for i in self.lead_list_items
            if not (i["list_id"] == list_id and i["tenant_id"] == tenant_id)
        ]
        return fore - len(self.lead_list_items)

    async def stada_hangande_leadsjobb(
        self, tenant_id: str, *, aldre_an_minuter: int, utom: list[str] | None = None
    ) -> list[str]:
        # Speglar UPDATE ... RETURNING i postgres.py: samma statusar, samma
        # klocka (updated_at), pausade körningar orörda, completed_at sätts.
        grans = datetime.now(timezone.utc) - timedelta(minutes=aldre_an_minuter)
        undantag = set(utom or ())
        stadade: list[str] = []
        for rad in self.leads_job_ledger.values():
            if (
                rad["tenant_id"] == tenant_id
                and rad["status"] in ("queued", "processing")
                and rad["job_id"] not in undantag
                and (rad.get("korning") or {}).get("styrning") != "paus"
                and datetime.fromisoformat(rad.get("updated_at") or rad["created_at"]) < grans
            ):
                rad["status"] = "failed"
                rad["completed_at"] = _now()
                stadade.append(rad["job_id"])
        return stadade

    async def stada_hangande_leadslistor(
        self,
        tenant_id: str,
        *,
        aldre_an_minuter: int,
        felorsak: str,
        utom: list[str] | None = None,
    ) -> list[str]:
        grans = datetime.now(timezone.utc) - timedelta(minutes=aldre_an_minuter)
        undantag = set(utom or ())
        stadade: list[str] = []
        for rad in self.lead_lists.get(tenant_id, []):
            if (
                rad["status"] in ("bestalld", "byggs")
                and rad["id"] not in undantag
                and datetime.fromisoformat(rad["created_at"]) < grans
            ):
                rad["status"] = "fel"
                rad["felorsak"] = felorsak
                rad["completed_at"] = _now()
                stadade.append(rad["id"])
        for list_id in stadade:
            await self.rensa_lead_list_items(tenant_id, list_id)
        return stadade

    async def sum_leads_tokens(self, tenant_id: str, *, hours: int = 24) -> int:
        # Speglar SQL-frågan i postgres.py: leads-typerna, tidsfönster,
        # tokens_in + tokens_out, testkörningar MEDräknade.
        return self._sum_tokens(tenant_id, LEADS_BUDGET_AGENT_TYPES, hours)

    async def sum_support_tokens(self, tenant_id: str, *, hours: int = 24) -> int:
        return self._sum_tokens(tenant_id, SUPPORT_BUDGET_AGENT_TYPES, hours)

    async def daily_support_usage(
        self, tenant_id: str, *, days: int = 30
    ) -> list[dict[str, Any]]:
        # Speglar SQL-frågan i postgres.py: gruppera per dag, nyaste först,
        # dagar utan körningar utelämnas.
        granser = datetime.now(timezone.utc) - timedelta(days=days)
        per_dag: dict[str, dict[str, int]] = {}
        for r in self.agent_runs.get(tenant_id, []):
            if r["agent_type"] not in SUPPORT_BUDGET_AGENT_TYPES:
                continue
            skapad = datetime.fromisoformat(r["created_at"])
            if skapad < granser:
                continue
            dag = per_dag.setdefault(
                skapad.date().isoformat(),
                {"korningar": 0, "korningar_test": 0, "tokens_in": 0, "tokens_out": 0},
            )
            dag["korningar_test" if r.get("is_test") else "korningar"] += 1
            dag["tokens_in"] += int(r.get("tokens_in") or 0)
            dag["tokens_out"] += int(r.get("tokens_out") or 0)
        return [
            {"datum": datum, **varden}
            for datum, varden in sorted(per_dag.items(), reverse=True)
        ]

    def _sum_tokens(self, tenant_id: str, agent_types: tuple[str, ...], hours: int) -> int:
        granser = datetime.now(timezone.utc) - timedelta(hours=hours)
        total = 0
        for r in self.agent_runs.get(tenant_id, []):
            if r["agent_type"] not in agent_types:
                continue
            if datetime.fromisoformat(r["created_at"]) < granser:
                continue
            total += int(r.get("tokens_in") or 0) + int(r.get("tokens_out") or 0)
        return total

    async def support_oversikt_underlag(
        self, tenant_id: str, *, sedan: str, is_test: bool | None
    ) -> dict[str, Any]:
        # Speglar SQL-varianten i postgres.py: samma urval, samma fält.
        def _tid(iso: str | None) -> datetime | None:
            if not iso:
                return None
            t = datetime.fromisoformat(iso)
            return t if t.tzinfo else t.replace(tzinfo=timezone.utc)

        fran = _tid(sedan)
        svar: dict[str, datetime] = {}
        for d in self.decisions:
            if d["tenant_id"] != tenant_id or d["event"] not in ("auto_sent", "approved_and_sent"):
                continue
            eid = d.get("email_id")
            tid = _tid(d["created_at"])
            if eid and tid and (eid not in svar or tid < svar[eid]):
                svar[eid] = tid

        mejl = []
        for e in self.emails.values():
            if e["tenant_id"] != tenant_id:
                continue
            if e["status"] in ("att_hantera", "lead", "ej_relaterat"):
                continue
            if (e.get("klass") or "support") != "support":
                continue
            if is_test is not None and bool(e.get("is_test")) != is_test:
                continue
            mottaget = _tid(e["received_at"])
            if fran and mottaget and mottaget < fran:
                continue
            c = self.classifications.get(e["id"]) or {}
            kallor = c.get("kb_sources")
            forsta = svar.get(e["id"])
            mejl.append(
                {
                    "id": e["id"],
                    "received_at": mottaget.isoformat() if mottaget else e["received_at"],
                    "status": e["status"],
                    "category": c.get("category"),
                    "escalate": c.get("escalate"),
                    "kb_traffar": len(kallor) if isinstance(kallor, list) else None,
                    "forsta_svar": forsta.isoformat() if forsta else None,
                }
            )

        korningar = [
            r
            for r in self.agent_runs.get(tenant_id, [])
            if r["agent_type"] == "support"
            and not r.get("is_test")
            and (not fran or (_tid(r["created_at"]) or fran) >= fran)
        ]
        modeller: dict[str, int] = {}
        for r in korningar:
            m = r.get("model")
            if m and m != "svarscache":
                modeller[m] = modeller.get(m, 0) + 1
        return {
            "mejl": mejl,
            "korningar": {
                "antal": len(korningar),
                "tokens_in": sum(int(r.get("tokens_in") or 0) for r in korningar),
                "tokens_out": sum(int(r.get("tokens_out") or 0) for r in korningar),
                "cache": sum(1 for r in korningar if r.get("model") == "svarscache"),
                "modell": max(modeller, key=lambda k: modeller[k]) if modeller else None,
            },
            "kb_artiklar": len(self.kb.get(tenant_id, [])),
        }

    async def weekly_analytics(self, tenant_id: str, *, weeks: int = 8) -> dict[str, Any]:
        # Speglar SQL-varianten i postgres.py, inklusive de tomma veckorna:
        # serien byggs ur kalendern, inte ur raderna. Skulle den här räkna på
        # ett annat sätt vore testsviten grön mot en aggregering produktionen
        # aldrig kör — samma klass av fel som AGENT_RUN_TYPES finns för.
        weeks = max(1, min(weeks, 52))

        nu = datetime.now(timezone.utc)
        start_denna = (nu - timedelta(days=nu.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        veckostarter = [start_denna - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]

        def vecka_for(iso: str | None) -> datetime | None:
            if not iso:
                return None
            try:
                stämpel = datetime.fromisoformat(iso)
            except ValueError:
                return None
            if stämpel.tzinfo is None:
                stämpel = stämpel.replace(tzinfo=timezone.utc)
            return (stämpel - timedelta(days=stämpel.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        meddelanden = self.outreach_messages.get(tenant_id, [])
        körningar = self.agent_runs.get(tenant_id, [])
        ärenden = [t for t in self.tickets.values() if t["tenant_id"] == tenant_id]

        rader = []
        for start in veckostarter:
            i_veckan = lambda rows, nyckel: [  # noqa: E731
                r for r in rows if vecka_for(r.get(nyckel)) == start
            ]
            skickade = i_veckan(meddelanden, "sent_at")
            veckans_körningar = [
                r for r in i_veckan(körningar, "created_at") if not r.get("is_test")
            ]
            veckans_ärenden = i_veckan(ärenden, "created_at")

            rader.append(
                {
                    "week": f"v{start.isocalendar().week}",
                    "start": start.isoformat(),
                    "sent": sum(1 for m in skickade if m["direction"] == "outbound"),
                    "replies": sum(1 for m in skickade if m["direction"] == "inbound"),
                    "leads_runs": sum(
                        1 for r in veckans_körningar if r["agent_type"].startswith("leads")
                    ),
                    "support_runs": sum(
                        1 for r in veckans_körningar if r["agent_type"] == "support"
                    ),
                    "tickets": len(veckans_ärenden),
                    "escalated": sum(1 for t in veckans_ärenden if t["status"] == "escalated"),
                    "resolved": sum(
                        1 for t in veckans_ärenden if t["status"] in ("resolved", "closed")
                    ),
                    "new_leads": len(
                        [p for p in i_veckan(self.prospects.get(tenant_id, []), "created_at")
                         if p.get("origin") not in ("example", "test")]
                    ),
                }
            )

        return {"weeks": rader, "coverage": ANALYTICS_COVERAGE}

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
        is_test: bool = False,
        automatutskick: bool = False,
        mailbox_id: str | None = None,
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
            "is_test": is_test,
            "automatutskick": automatutskick,
            "mailbox_id": mailbox_id,
            "hanterad_at": None,
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

    async def delete_mock_emails(self, tenant_id: str, *, category: str | None = None) -> int:
        """Se Storage.delete_mock_emails."""
        träffar = [
            email
            for email in self.emails.values()
            if email["tenant_id"] == tenant_id
            and email["provider"] == "mock"
            and (
                category is None
                or (self.classifications.get(email["id"]) or {}).get("category") == category
            )
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
        is_test: bool | None = False,
        inkludera_larm: bool = False,
        klass: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = [e for e in self.emails.values() if e["tenant_id"] == tenant_id]
        rows.sort(key=lambda e: e["received_at"], reverse=True)
        result = []
        needle = (search or "").lower()
        for email in rows:
            if is_test is not None and bool(email.get("is_test")) != is_test:
                continue
            summary = self._email_summary(email)
            if status and summary["status"] != status:
                continue
            # Samma som postgres: utan statusfilter syns inte larmen (078),
            # och utan klassfilter inte leads eller dolda (084).
            if not status and not inkludera_larm and summary["status"] == "att_hantera":
                continue
            if klass is not None and summary.get("klass") != klass:
                continue
            if klass is None and not status and not inkludera_larm and summary["status"] in ("lead", "ej_relaterat"):
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
        is_test: bool | None = None,
        hanterad: bool | None = None,
        klass: str | None = None,
        klass_kalla: str | None = None,
    ) -> dict[str, Any] | None:
        email = self.emails.get(email_id)
        if not email or email["tenant_id"] != tenant_id:
            return None
        if status:
            email["status"] = status
        if klass is not None:
            if klass not in ("support", "lead", "ej_relaterat"):
                raise ValueError(f"klass={klass!r} bryter mot ss_emails-checken (084).")
            email["klass"] = klass
        if klass_kalla is not None:
            email["klass_kalla"] = klass_kalla
        if ticket_id:
            email["ticket_id"] = ticket_id
        if is_test is not None:
            email["is_test"] = is_test
        if hanterad is not None:
            # Speglar SQL:en: True stämplar bara en ostämplad rad, False nollar.
            if hanterad:
                email["hanterad_at"] = email.get("hanterad_at") or _now()
            else:
                email["hanterad_at"] = None
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
        offertforfragan: bool = False,
        utbildningsintresse: bool = False,
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
            "offertforfragan": offertforfragan,
            "utbildningsintresse": utbildningsintresse,
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

    async def list_replies(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        # Speglar SQL-varianten: inbound över alla trådar, senast först, med
        # prospektets namn hopslaget. En avvikelse här hade gett en grön svit
        # mot en aggregering produktionen aldrig kör.
        limit = max(1, min(limit, 200))

        trådar = self.outreach_threads.get(tenant_id, {})
        prospekt = {p["id"]: p for p in self.prospects.get(tenant_id, [])}

        svar = []
        for m in self.outreach_messages.get(tenant_id, []):
            if m["direction"] != "inbound":
                continue
            tråd = trådar.get(m["thread_id"]) or {}
            p = prospekt.get(tråd.get("prospect_id")) or {}
            svar.append(
                {
                    "id": m["id"],
                    "body": m["body"],
                    "sent_at": m.get("sent_at"),
                    "thread_id": m["thread_id"],
                    "company_name": p.get("company_name"),
                    "contact_name": p.get("contact_name"),
                    "contact_email": p.get("contact_email"),
                    "status": p.get("status"),
                }
            )

        # `order by sent_at desc nulls last`. Med reverse=True hamnar rader SOM
        # HAR sent_at först (True > False), och inom dem den senaste först.
        svar.sort(key=lambda r: (r["sent_at"] is not None, r["sent_at"] or ""), reverse=True)
        return svar[:limit]

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

    # -- Instruktionslagret (migration 049) ---------------------------------

    async def get_global_instructions(self, agent_type: str = "alla") -> dict[str, Any] | None:
        return next(
            (dict(rad) for rad in self.global_instructions if rad["aktiv"] and rad["agent_type"] == agent_type),
            None,
        )

    async def get_global_instruction(self, instruktion_id: str) -> dict[str, Any] | None:
        return next((dict(rad) for rad in self.global_instructions if rad["id"] == instruktion_id), None)

    async def save_global_instructions(
        self,
        *,
        ravtext: str,
        strukturerad_md: str,
        kalla: str = "ai",
        uppdaterad_av: str | None = None,
        agent_type: str = "alla",
        feedback: str = "",
    ) -> dict[str, Any]:
        for rad in self.global_instructions:
            if rad["agent_type"] == agent_type:
                rad["aktiv"] = False
        rad = {
            "id": str(uuid.uuid4()),
            "agent_type": agent_type,
            "feedback": feedback,
            "ravtext": ravtext,
            "strukturerad_md": strukturerad_md,
            "kalla": kalla,
            "aktiv": True,
            "uppdaterad_av": uppdaterad_av,
            "created_at": datetime.now(timezone.utc),
        }
        self.global_instructions.insert(0, rad)
        return dict(rad)

    async def list_global_instructions(
        self, *, limit: int = 20, agent_type: str = "alla", med_text: bool = False
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": rad["id"],
                "agent_type": rad["agent_type"],
                "kalla": rad["kalla"],
                "aktiv": rad["aktiv"],
                "uppdaterad_av": rad["uppdaterad_av"],
                "created_at": rad["created_at"],
                "ravtext_tecken": len(rad["ravtext"]),
                "strukturerad_tecken": len(rad["strukturerad_md"]),
                **({"strukturerad_md": rad["strukturerad_md"], "feedback": rad["feedback"]} if med_text else {}),
            }
            for rad in [r for r in self.global_instructions if r["agent_type"] == agent_type][:limit]
        ]

    async def get_agent_config(self, tenant_id: str, *, agent_type: str) -> dict[str, Any]:
        rad = self.agent_instructions.get((tenant_id, agent_type))
        return dict(rad) if rad else {
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
        rad = await self.get_agent_config(tenant_id, agent_type=agent_type)
        rad["instructions_md"] = instructions_md
        rad["instructions_rav"] = instructions_rav
        # None = rör inte tonen, "" = nollställ den. Samma semantik som
        # PostgresStorage — MemoryStorage får aldrig sacka efter protokollet.
        if tone is not None:
            rad["tone"] = tone
        self.agent_instructions[(tenant_id, agent_type)] = rad
        return dict(rad)

    async def list_review_queue(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        # Speglar Postgres-joinen: väntande meddelandets text plus prospektets
        # mottagar- och lägesfält.
        trader = self.outreach_threads.get(tenant_id, {})
        prospekt = {p["id"]: p for p in self.prospects.get(tenant_id, [])}
        svar: list[dict[str, Any]] = []
        for item in self.send_queue.get(tenant_id, []):
            if item["status"] != "awaiting_review":
                continue
            m = await self.get_pending_outreach_message(tenant_id, item["thread_id"]) or {}
            p = prospekt.get((trader.get(item["thread_id"]) or {}).get("prospect_id"), {})
            svar.append({
                **item,
                "subject": m.get("subject"),
                "body": m.get("body"),
                "message_id": m.get("id"),
                "prospect_id": p.get("id"),
                "prospect_email": p.get("contact_email"),
                "company_name": p.get("company_name"),
                "contact_name": p.get("contact_name"),
                "contact_role": p.get("contact_role"),
                "website": p.get("website"),
                "lagesbeskrivning": p.get("lagesbeskrivning"),
                "signaler": p.get("signaler"),
            })
        svar.sort(key=lambda r: str(r.get("scheduled_at") or ""))
        return svar[:limit]

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
            detaljer = self.customer_details.get(tid, {})
            rows.append(
                {
                    **tenant,
                    # Samma coalesce som Postgres-frågan: registrets datum
                    # vinner, annars tenantens skapelsedatum. Avtalet är null
                    # tills någon registrerat ett — null ÄR "inget avtal".
                    "kund_sedan": detaljer.get("kund_sedan")
                    or (
                        tenant["created_at"].date()
                        if isinstance(tenant.get("created_at"), datetime)
                        else tenant.get("created_at")
                    ),
                    "avtal_signerat": detaljer.get("avtal_signerat"),
                    # Speglar Postgres-frågans workspaces.products. Minnet har
                    # inga arbetsytor, så nyckeln finns men är None om inte ett
                    # test satt produkter på tenanten — samma "ingen kopplad
                    # arbetsyta" som SQL:en ger.
                    "active": tenant.get("active", True),
                    # Speglar Postgres t.status (080): etiketten följer spärren
                    # när inget test satt den uttryckligen.
                    "status": tenant.get(
                        "status", "aktiv" if tenant.get("active", True) else "avstangd"
                    ),
                    "products": tenant.get("products"),
                    # Speglar Postgres-frågans workspaces.trial_slut (074).
                    "trial_slut": tenant.get("trial_slut"),
                    "tickets": sum(1 for t in self.tickets.values() if t["tenant_id"] == tid),
                    "escalated": sum(
                        1
                        for t in self.tickets.values()
                        if t["tenant_id"] == tid and t.get("status") == "escalated"
                    ),
                    # Speglar Postgres exakt. Att räkna alla här och filtrera
                    # där hade gett en grön svit mot en vy som visar fel tal i
                    # drift — se doktrinen i storage/base.py.
                    "runs": sum(1 for r in runs if not r.get("is_test")),
                    "test_runs": sum(1 for r in runs if r.get("is_test")),
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
        prospect_id: str | None = None,
    ) -> list[dict[str, Any]]:
        runs = [
            run
            for tid, tenant_runs in self.agent_runs.items()
            if tenant_id is None or tid == tenant_id
            for run in tenant_runs
        ]
        if agent_type:
            runs = [r for r in runs if r["agent_type"] == agent_type]
        if prospect_id:
            runs = [r for r in runs if str(r.get("prospect_id") or "") == str(prospect_id)]
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

    # -- Kundregister (migration 053) ---------------------------------------
    #
    # Samma normalisering som Postgres-sidan, via normalisera_kunddata i
    # base.py. En lagring som tar emot mer än den andra är hur
    # agent_type-buggen levde ett halvår med grön svit.

    async def get_customer_details(self, tenant_id: str) -> dict[str, Any] | None:
        rad = self.customer_details.get(tenant_id)
        return dict(rad) if rad else None

    async def upsert_customer_details(
        self, tenant_id: str, falt: dict[str, Any]
    ) -> dict[str, Any]:
        andringar = normalisera_kunddata(falt)
        rad = self.customer_details.setdefault(
            tenant_id, {"tenant_id": tenant_id}
        )
        rad.update(andringar)
        rad["updated_at"] = _now()
        return dict(rad)

    async def list_customer_contacts(self, tenant_id: str) -> list[dict[str, Any]]:
        kontakter = [
            dict(k) for k in self.customer_contacts if k["tenant_id"] == tenant_id
        ]
        kontakter.sort(key=lambda k: k["created_at"])
        return kontakter

    async def create_customer_contact(
        self,
        tenant_id: str,
        *,
        namn: str,
        roll: str | None = None,
        mejl: str | None = None,
        telefon: str | None = None,
    ) -> dict[str, Any]:
        kontakt = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "namn": namn.strip(),
            "roll": (roll or "").strip() or None,
            "mejl": (mejl or "").strip() or None,
            "telefon": (telefon or "").strip() or None,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.customer_contacts.append(kontakt)
        return dict(kontakt)

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
        for kontakt in self.customer_contacts:
            # Båda villkoren: ett kontakt-id ur en annan kunds lista ska ge
            # None (404), inte en uppdatering över tenant-gränsen.
            if kontakt["id"] == contact_id and kontakt["tenant_id"] == tenant_id:
                if namn is not None and namn.strip():
                    kontakt["namn"] = namn.strip()
                for falt, varde in (("roll", roll), ("mejl", mejl), ("telefon", telefon)):
                    if varde is not None:
                        kontakt[falt] = varde.strip() or None
                kontakt["updated_at"] = _now()
                return dict(kontakt)
        return None

    async def delete_customer_contact(self, tenant_id: str, contact_id: str) -> bool:
        fore = len(self.customer_contacts)
        self.customer_contacts = [
            k
            for k in self.customer_contacts
            if not (k["id"] == contact_id and k["tenant_id"] == tenant_id)
        ]
        return len(self.customer_contacts) < fore

    # -- Bokföring (migration 045) ------------------------------------------
    #
    # Samma validering som Postgres-sidan, inte bara samma signatur. En lagring
    # som TAR EMOT mer än den andra är hur agent_type-buggen kunde leva i ett
    # halvår med grön testsvit — se log_agent_run ovan.

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
        betalstatus: str | None = None,
        anmarkning: str = "",
        kalla: str = "uppladdning",
        mejl_id: str | None = None,
        mejl_amne: str | None = None,
        mejl_avsandare: str | None = None,
        valuta: str = "SEK",
        belopp_original: str | None = None,
        granskning: dict[str, Any] | None = None,
        granskningsstatus: str | None = None,
    ) -> dict[str, Any]:
        kontrollera_bk_status(status)
        kontrollera_bk_riktning(riktning)
        kontrollera_bk_betalstatus(betalstatus)
        kontrollera_bk_kalla(kalla)
        kontrollera_bk_granskningsstatus(granskningsstatus)
        rad = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "sha256": sha256,
            "filnamn": filnamn,
            "mimetyp": mimetyp,
            "status": status,
            # ISO-sträng, inte date: _row i postgres.py isoformatar allt med
            # .isoformat(), så ett date-objekt här hade gjort minnet och
            # produktionen olika för samma anrop. Se base.bk_datum.
            "datum": _iso(bk_datum(datum)),
            "motpart": motpart,
            "brutto": bk_belopp(brutto, "brutto"),
            "momssats": bk_belopp(momssats, "momssats"),
            "riktning": riktning,
            "kategori": kategori,
            "betalstatus": betalstatus,
            "anmarkning": anmarkning,
            "kalla": kalla,
            "mejl_id": mejl_id,
            "mejl_amne": mejl_amne,
            "mejl_avsandare": mejl_avsandare,
            "valuta": valuta,
            "belopp_original": belopp_original,
            # Rundtur genom JSON: Postgres lagrar jsonb, och en dict med
            # Decimal i hade sett rätt ut här men fallit vid första riktiga
            # skrivningen.
            "granskning": None if granskning is None else json.loads(json.dumps(granskning)),
            "granskningsstatus": granskningsstatus,
            "created_at": _now(),
        }
        self.bk_underlag.setdefault(tenant_id, []).append(rad)
        return dict(rad)

    async def markera_kvittomejl_last(
        self, tenant_id: str, fingeravtryck: str, *, klass: str
    ) -> None:
        self.kvittomejl_lasta.setdefault(tenant_id, {}).setdefault(fingeravtryck, klass)

    async def ar_kvittomejl_last(self, tenant_id: str, fingeravtryck: str) -> bool:
        return fingeravtryck in self.kvittomejl_lasta.get(tenant_id, {})

    async def get_bk_underlag(self, tenant_id: str, underlag_id: str) -> dict[str, Any] | None:
        for rad in self.bk_underlag.get(tenant_id, []):
            if rad["id"] == underlag_id:
                return dict(rad)
        return None

    async def get_bk_underlag_by_sha256(
        self, tenant_id: str, sha256: str
    ) -> dict[str, Any] | None:
        # Listan är append-ordnad, så första träffen ÄR den äldsta — samma
        # rad Postgres-sidan väljer med `order by created_at`.
        for rad in self.bk_underlag.get(tenant_id, []):
            if rad["sha256"] == sha256:
                return dict(rad)
        return None

    async def list_bk_underlag(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        träffar = []
        for rad in self.bk_underlag.get(tenant_id, []):
            datum = rad.get("datum")
            # Ett underlag UTAN datum tas med: det är just ett sådant grinden
            # fällt, och en granskningskö som gömmer dem är ingen kö.
            #
            # Jämförelsen sker på ISO-strängar. Det är korrekt och inte en
            # genväg: ÅÅÅÅ-MM-DD sorterar lexikografiskt i samma ordning som
            # kronologiskt, vilket är hela skälet till att formatet ser ut så.
            if datum is not None:
                if fran and datum < _iso(bk_datum(fran)):
                    continue
                if till and datum > _iso(bk_datum(till)):
                    continue
            träffar.append(dict(rad))
        träffar.sort(key=lambda r: (r["datum"] is None, r["datum"] or "", r["created_at"]))
        return träffar[:limit]

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
        betalstatus: str | None = None,
        anmarkning: str | None = None,
    ) -> dict[str, Any] | None:
        if status is not None:
            kontrollera_bk_status(status)
        if riktning is not None:
            kontrollera_bk_riktning(riktning)
        if betalstatus is not None:
            kontrollera_bk_betalstatus(betalstatus)
        for rad in self.bk_underlag.get(tenant_id, []):
            if rad["id"] != underlag_id:
                continue
            for nyckel, värde in (
                ("status", status),
                ("datum", _iso(bk_datum(datum))),
                ("motpart", motpart),
                ("brutto", bk_belopp(brutto, "brutto")),
                ("momssats", bk_belopp(momssats, "momssats")),
                ("riktning", riktning),
                ("kategori", kategori),
                ("betalstatus", betalstatus),
                ("anmarkning", anmarkning),
            ):
                if värde is not None:
                    rad[nyckel] = värde
            return dict(rad)
        return None

    async def create_bk_verifikat(
        self,
        tenant_id: str,
        *,
        underlag_id: str,
        serie: str,
        nummer: str | None = None,
        datum: date,
        text: str,
        rader: list[dict[str, Any]],
    ) -> dict[str, Any]:
        kontrollera_bk_balans(rader)
        if nummer is None:
            # Nästa lediga i serien — högsta befintliga plus ett, inte
            # listlängden plus ett: ett explicit satt nummer (SIE-import)
            # skulle annars kollidera med nästa automatiska.
            befintliga = [
                int(p["nummer"])
                for p in self.bk_verifikat.get(tenant_id, [])
                if p["serie"] == serie and str(p["nummer"]).isdigit()
            ]
            nummer = str(max(befintliga, default=0) + 1)
        post = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "underlag_id": underlag_id,
            "serie": serie,
            "nummer": nummer,
            "datum": _iso(bk_datum(datum)),
            "text": text,
            "rader": [
                {
                    "konto": str(r["konto"]),
                    "debet": bk_belopp(r.get("debet"), "debet") or Decimal(0),
                    "kredit": bk_belopp(r.get("kredit"), "kredit") or Decimal(0),
                    "text": r.get("text", ""),
                }
                for r in rader
            ],
            "created_at": _now(),
        }
        self.bk_verifikat.setdefault(tenant_id, []).append(post)
        return dict(post)

    async def list_bk_verifikat(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
    ) -> list[dict[str, Any]]:
        träffar = []
        for post in self.bk_verifikat.get(tenant_id, []):
            if fran and post["datum"] < _iso(bk_datum(fran)):
                continue
            if till and post["datum"] > _iso(bk_datum(till)):
                continue
            träffar.append(dict(post))
        träffar.sort(key=lambda p: (p["datum"], p["nummer"]))
        return träffar

    async def rensa_bk_period(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
    ) -> int:
        # Urvalet läses ur `list_bk_underlag` i stället för att skrivas om här.
        # En andra filtrering som ser likadan ut hade glidit isär från listans
        # första gången någon rörde datumlogiken — och då raderar knappen ett
        # annat urval än det vyn visade. `limit` sätts högt av samma skäl:
        # listan visar 200 åt gången, medan rensningen gäller hela perioden.
        att_radera = await self.list_bk_underlag(
            tenant_id, fran=fran, till=till, limit=1_000_000
        )
        ider = {rad["id"] for rad in att_radera}
        if not ider:
            return 0

        self.bk_underlag[tenant_id] = [
            rad for rad in self.bk_underlag.get(tenant_id, []) if rad["id"] not in ider
        ]
        # Postgres gör det här med `on delete cascade`. Minnet har ingen
        # främmande nyckel, så kaskaden skrivs för hand — utan den blir
        # verifikaten kvar, och perioden fortsätter räknas ur poster vars
        # underlag inte längre finns.
        self.bk_verifikat[tenant_id] = [
            post
            for post in self.bk_verifikat.get(tenant_id, [])
            if post["underlag_id"] not in ider
        ]
        return len(ider)

    async def close(self) -> None:
        return None
