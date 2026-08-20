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

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None: ...

    async def list_tenants(self) -> list[dict[str, Any]]: ...

    # -- Inkorgar -----------------------------------------------------------

    async def list_mailboxes(self, tenant_id: str) -> list[dict[str, Any]]: ...

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

    async def get_channel_config(self, tenant_id: str, channel: str) -> dict[str, Any]: ...

    async def get_agent_taxonomy(self, tenant_id: str) -> tuple[str, ...]:
        """A4: kundkonfigurerbar ärendetaxonomi. Tomt/saknat agent_configs-rad
        -> global default (config.CATEGORIES)."""
        ...

    # -- Leads: kontextdokument (Fas A, Del C punkt 1) -----------------------

    async def save_context_doc(
        self, tenant_id: str, *, kind: str, content: str, source: str = ""
    ) -> dict[str, Any]: ...

    async def list_context_docs(
        self, tenant_id: str, *, kind: str | None = None
    ) -> list[dict[str, Any]]: ...

    async def get_latest_context_doc(self, tenant_id: str, *, kind: str) -> dict[str, Any] | None:
        """Senaste versionen av en given kind — det kontextpaketet faktiskt läser."""
        ...

    # -- Leads: send_queue-schemaläggaren (Del J, Fas C-E) -------------------

    async def list_due_send_queue(self, tenant_id: str, now: Any) -> list[dict[str, Any]]:
        """status='queued' och scheduled_at <= now."""
        ...

    async def update_send_queue_status(
        self, tenant_id: str, item_id: str, *, status: str, gate_checks: dict[str, Any]
    ) -> None: ...

    async def get_outreach_thread(self, tenant_id: str, thread_id: str) -> dict[str, Any] | None: ...

    async def get_pending_outreach_message(
        self, tenant_id: str, thread_id: str
    ) -> dict[str, Any] | None:
        """Det äldsta outbound-meddelandet i tråden utan sent_at."""
        ...

    async def mark_outreach_message_sent(self, tenant_id: str, message_id: str, sent_at: Any) -> None: ...

    async def list_outreach_messages(
        self, tenant_id: str, thread_id: str
    ) -> list[dict[str, Any]]:
        """Alla meddelanden i en tråd, äldst först. Schemaläggaren räknar
        sekvensindex ur den här i stället för ur en räknarkolumn — en räknare
        kan glida isär med verkligheten, och det här avgör om ett mejl går ut
        utan mänsklig granskning."""
        ...

    # -- Leads: underlaget send_guard dömer på (DEL 2.3) --------------------
    #
    # VARJE metod här har en motsvarighet i BÅDE MemoryStorage och
    # PostgresStorage, med samma validering. Det var precis den luckan som
    # dolde agent_type-buggen i månader: en väg som fungerade i minnet och
    # tyst gjorde något annat mot Postgres.

    async def list_suppressions(self, tenant_id: str) -> set[str]:
        """Adresser som avregistrerat sig. Gäller HELA tenanten, inte en
        enskild kampanj — en avregistrering som bara gällde kampanjen hade
        gjort löftet i mejlet till ett brutet löfte."""
        ...

    async def add_suppression(self, tenant_id: str, *, email: str, reason: str) -> None:
        """Skrivs av avregistreringslänken. Ska gälla omedelbart."""
        ...

    async def count_sent_outreach(self, tenant_id: str, *, since: Any = None) -> int:
        """Antal FAKTISKT skickade utgående meddelanden. Räknas ur sent_at och
        inte ur send_queue-status, eftersom det är sent_at som betyder att ett
        mejl lämnat huset."""
        ...

    async def last_contact_with_company(
        self, tenant_id: str, foretagsnyckel: str
    ) -> Any | None:
        """När bolaget senast kontaktades, oavsett kontaktperson. Nyckeln är
        FÖRETAGET — ett bolag som byter kontaktperson ska inte kunna få ett
        nytt kallmejl dagen efter."""
        ...

    # -- G11: segmentaggregatet (den enda avsiktliga tenantgränsöverskridningen) --

    async def get_segment_ab_aggregate(self) -> list[dict[str, Any]]:
        """Inget tenant_id-argument — se app/leads/segment_aggregate.py och
        migration 013 för varför det är avsiktligt."""
        ...

    # -- G10: revisionslogg per agentkörning --------------------------------

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
        """Skrivs för VARJE körning. Krävs för DSAR och för att kunna felsöka
        ett dåligt svar i efterhand (plan G10).

        `is_test` märker körningar startade från adminytans testyta. De skrivs
        som alla andra men får aldrig räknas som kundvolym — se migration 036.
        Parametern står i PROTOKOLLET och inte bara i Postgres-implementationen,
        eftersom en signatur som skiljer sig mellan lagren är exakt hur
        agent_runs kunde avvisa varje leads-körning i ett halvår med grön
        testsvit."""
        ...

    async def list_agent_runs(
        self, tenant_id: str, *, agent_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]: ...

    # -- Skill-spegeln (INV-SKILL-007) --------------------------------------
    #
    # Ingen tenant_id: delad baselinekatalog, samma avsiktliga undantag som
    # get_segment_ab_aggregate. PostgresStorage använder därför inte _scoped()
    # här — det är inte en glömd RLS-scoping, det finns ingen kolumn att
    # scopa på (se migration 016).

    async def list_skill_files(
        self, *, manifest_hash: str
    ) -> list[dict[str, Any]]:
        """Alla speglade filer för EN manifest_hash. Uppslagning sker alltid
        på den lokalt utcheckade hashen, vilket gör versionsskev strukturellt
        omöjlig."""
        ...

    async def publish_skill_files(
        self, *, manifest_hash: str, rows: list[dict[str, Any]], published_by: str = ""
    ) -> int:
        """Idempotent publicering. Returnerar antal nya rader."""
        ...

    # -- Leads: skriva ett utkast + köa (aldrig skicka, INV-SEC-004) --------

    async def queue_outreach_message(
        self,
        tenant_id: str,
        *,
        thread_id: str,
        body: str,
        subject: str,
        humanizer_variant: str,
        scheduled_at: Any,
        status: str = "queued",
    ) -> dict[str, Any]:
        """Skapar meddelandet (sent_at=NULL) OCH send_queue-raden i samma
        operation — det finns ingen kodväg som skapar det ena utan det andra.

        `status` avgörs av kundens autonominivå (app/leads/autonomy.py):
        'queued' släpps till schemaläggaren, 'awaiting_review' väntar på att
        en människa godkänner. Default är 'queued' för att inte ändra
        beteendet för anropare som inte känner till nivån."""
        ...

    # -- Leads: proveniensregister (Fas B, INV-DATA-001, research-verktygets allowlist) --

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
        """Ingången till hela leads-pipelinen. Utan den här fanns inget sätt
        att skapa ett prospekt alls — research/outreach kunde aldrig köras."""
        ...

    async def get_prospect(self, tenant_id: str, prospect_id: str) -> dict[str, Any] | None: ...

    async def list_prospects(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]: ...

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
        """Fas B:s bedömning (icp_fit, qualified, disqualifiers) landar här,
        migration 024. Innan den fanns räknades icp_fit ut av modellen och
        kastades bort — den gick inte att sortera, mäta eller motivera i
        efterhand."""
        ...

    async def create_prospect_source(
        self,
        tenant_id: str,
        *,
        prospect_id: str,
        source_url: str,
        source_type: str,
        lawful_basis: str,
    ) -> dict[str, Any]: ...

    async def list_prospect_source_urls(self, tenant_id: str, prospect_id: str) -> set[str]:
        """URL:er redan registrerade som källor för prospektet — det
        app/agent/research_tools.py:s skrapningsverktyg kontrollerar
        url-argumentet mot innan det gör ett riktigt nätverksanrop."""
        ...

    async def log_metric(
        self, tenant_id: str, *, ticket_id: str | None, metric_name: str, value: float | None
    ) -> None: ...

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

    async def delete_emails_by_provider(self, tenant_id: str, provider: str) -> int:
        """Tar bort tenantens mail från EN provider. Returnerar antalet.

        Finns för "Hämta testmail", som ska BYTA UT demoinkorgen och inte fylla
        på den. Avgränsningen till provider är spärren: ett anrop kan aldrig
        träffa riktiga mail från IMAP eller API-ingesten, hur det än anropas.
        """
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
        self, tenant_id: str, *, tenant_name: str, raw_key: str
    ) -> dict[str, Any]: ...

    # -- Rate limiting (plattformsnivå, inte tenant-skopad) ------------------
    #
    # Ligger UTANFÖR tenant-skopet med flit: ett av tre scope är en IP-adress
    # från den anonyma demon, som per definition inte har någon tenant.

    async def count_rate_events(
        self, *, scope_kind: str, scope_id: str, kind: str, since: Any
    ) -> int: ...

    async def record_rate_events(
        self, *, scope_kind: str, scope_id: str, kind: str, count: int
    ) -> None: ...

    # -- Agentkonfiguration (autonomi + ICP, migration 023) ------------------

    async def get_agent_settings(self, tenant_id: str, *, agent_type: str) -> dict[str, Any]:
        """agent_configs.settings, eller {} om raden saknas. En saknad rad är
        inte ett fel — den betyder att kunden aldrig rört inställningarna, och
        då gäller defaultarna i autonomy.py."""
        ...

    async def set_agent_settings(
        self, tenant_id: str, *, agent_type: str, settings: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def list_review_queue(self, tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        """Utkast som väntar på granskning (send_queue.status='awaiting_review')."""
        ...

    # -- Admin: cross-tenant-läsning (Fas 6, kräver master-nyckel) ----------
    #
    # Ingen tenant_id-parameter är inte en glömd scoping — det ÄR poängen.
    # require_tenant avvisar master-nyckeln mot kunddata (deps.py), rätt
    # designat, och därför behöver admin-vyn en egen väg. Metoderna nedan
    # anropas ENBART från app/api/admin.py, som helt ligger bakom
    # require_master_key.
    #
    # Implementeras i BÅDA lagringarna. MemoryStorage får aldrig sacka efter
    # protokollet — det är precis så agent_runs.agent_type-buggen kunde gömma
    # sig i ett halvår.

    async def list_tenants_with_stats(self) -> list[dict[str, Any]]:
        """Alla tenants med nyckeltal: ärenden, körningar, tokens, senaste
        aktivitet."""
        ...

    async def list_agent_runs_all(
        self,
        *,
        tenant_id: str | None = None,
        agent_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    async def get_agent_run(self, run_id: str) -> dict[str, Any] | None: ...

    async def list_platform_events(
        self,
        *,
        level: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    async def log_platform_event(
        self,
        *,
        level: str,
        source: str,
        message: str,
        tenant_id: str | None = None,
        run_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None: ...

    async def close(self) -> None: ...


# Värdemängden för agent_runs.agent_type, spegel av check-villkoret i
# migration 025. Bor här, inte i respektive lagring, av ett skäl som kostade
# ett halvår att lära sig: villkoret fanns bara i Postgres, MemoryStorage tog
# emot vad som helst, testerna körde mot minnet och var gröna — samtidigt som
# ingen enda leads-körning sparades i produktion.
AGENT_RUN_TYPES = ("support", "leads", "leads_research", "leads_outreach", "demo")


# Framåtriktade statusövergångar, som i referensrepot (forward-only).
STATUS_ORDER = ["open", "in_progress", "escalated", "resolved", "closed"]


def status_transition_allowed(current: str, new: str) -> bool:
    try:
        return STATUS_ORDER.index(new) >= STATUS_ORDER.index(current)
    except ValueError:
        return False
