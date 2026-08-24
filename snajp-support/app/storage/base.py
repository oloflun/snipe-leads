"""Lagringsgränssnitt (multi-tenant).

Tabellstrukturen speglar referensarkitekturen (jawwad-ali/ai-customer-support-agent)
utökad med tenants: varje kunddatarad bär tenant_id och alla metoder tar tenant_id
som första parameter, så att varje kundföretag är helt isolerat. Två implementationer:

- PostgresStorage: Supabase Postgres + pgvector; sätter dessutom app.tenant_id per
  transaktion så RLS-policyerna i 003_snajp_multitenant.sql verkställs.
- MemoryStorage: in-memory med samma gränssnitt (graceful degradation utan databas).

Bokföringsdelen (`bk_*`) följer i stället dubbel bokföring som referens­arkitektur
— se lambdadevelopment/lambda-erp. Läst och härmad, inte vendorad.
"""

from datetime import date, datetime
from decimal import Decimal
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

    async def list_replies(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """Inkomna svar över ALLA trådar, senast först — arbetsytans Svar-flik.

        `list_outreach_messages` kräver ett thread_id och svarar därför på en
        annan fråga: "vad har sagts i den här tråden". Den här svarar på "vad
        har kommit in", vilket är det en människa öppnar fliken för att se.

        Prospektets namn följer med. Utan det blir listan en rad brödtexter utan
        avsändare, och den som läser måste slå upp varje tråd för hand för att
        veta vem som svarat.
        """
        ...

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

    async def avregistreringstoken(self, tenant_id: str, *, email: str) -> str:
        """Den ogenomskinliga token som gör avregistreringslänken klickbar.

        Idempotent per (tenant, adress): samma mottagare ska ha SAMMA länk i
        alla utskick. En ny token per mejl hade gjort den gamla länken i ett
        tidigare mejl till en död länk, och det är precis den länk någon
        letar upp när hen tröttnat.
        """
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

    async def weekly_analytics(self, tenant_id: str, *, weeks: int = 8) -> dict[str, Any]:
        """Veckovis utfall för kundens analysvy — EN tenant, aldrig aggregerat.

        Returnerar `{"weeks": [...], "coverage": {...}}` där varje vecka bär
        ISO-veckan och de tal som faktiskt går att räkna ur databasen.

        ## Varför `coverage` finns, och varför den inte får tas bort

        Kundens analysvy visade fram till nu `analyticsSeries` ur
        `lib/mock-data.ts` — v16–v21, 188 skick, 21 svar — för VARJE inloggad
        kund. Talen var påhittade och såg kompletta ut, vilket är den värsta
        kombinationen: ingen ifrågasätter en tabell som är fylld.

        `coverage` säger per mätvärde om det finns en källa alls. `meetings` är
        `false` här och kommer att vara det tills någon skriver bokade möten
        till databasen — autonominivån `meeting` i leads/autonomy.py har ingen
        produktionsanropare, så det finns ingenting att räkna. En nolla hade
        betytt "noll möten den här veckan"; `false` betyder "vi mäter det inte
        ännu". Frontenden visar det ena som en siffra och det andra som ett
        streck, och skillnaden är hela poängen med vyn.

        Metoden står i PROTOKOLLET och inte bara i Postgres-implementationen,
        av samma skäl som `record_agent_run` gör det ovan.
        """
        ...

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

    async def delete_mock_emails(self, tenant_id: str, *, category: str | None = None) -> int:
        """Tar bort testmail, valfritt bara ur ETT fack.

        Provider är hårdkodad till "mock" och inte en parameter: det är samma
        spärr som i `delete_emails_by_provider`, fast omöjlig att kringgå av en
        anropare som skickar fel sträng. Ett anrop kan aldrig träffa riktiga
        mail från IMAP eller API-ingesten.

        `category` läses ur den SENASTE klassificeringen. Ett mail som ännu
        inte hunnit klassificeras hör inte till något fack och rensas därför
        bara av det ofiltrerade anropet — annars hade "Uppdatera" i ett fack
        kunnat radera ärenden som just höll på att processas i ett annat.
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
        aktivitet.

        `runs` räknar KUNDVOLYM, alltså inte rader med `is_test`. `test_runs`
        redovisar våra egna provkörningar separat — de göms inte, de räknas bara
        inte som något kunden gjort. Tokens räknar båda: en provkörning kostar
        lika mycket som en riktig.
        """
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

    # -- Bokföring (migration 045) ------------------------------------------
    #
    # Belopp är `Decimal` genom hela kedjan, aldrig float — kolumnerna är
    # `numeric(14,2)` och asyncpg ger tillbaka Decimal. Se
    # app/bookkeeping/math.py för varför float avvisas.
    #
    # Filen sparas ALDRIG. `sha256` är allt som blir kvar av originalet, och
    # det räcker för att svara på "har vi sett det här kvittot förut?".

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
        """Ett underlag, med de fält avläsningen faktiskt hittade.

        Fälten är `None`-bara med flit: ett underlag där grinden fällt SKA gå
        att spara med hål i, annars finns ingen granskningskö att fylla.
        Grinden, inte databasen, avgör om det får bli en periodrapport.
        """
        ...

    async def get_bk_underlag(
        self, tenant_id: str, underlag_id: str
    ) -> dict[str, Any] | None: ...

    async def list_bk_underlag(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]: ...

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
        """Människans rättelse av ett fällt underlag. Bara satta fält skrivs."""
        ...

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
        """Verifikatet med sina konteringsrader, i EN transaktion.

        Rader och huvud i samma skrivning: ett verifikat utan rader balanserar
        inte, och ett halvskrivet verifikat är precis den sortens post som får
        en periodrapport att se rimlig ut och vara fel.
        """
        ...

    async def list_bk_verifikat(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
    ) -> list[dict[str, Any]]:
        """Verifikat med `rader` ifyllda. Sorterade på datum, sedan nummer."""
        ...

    async def close(self) -> None: ...


# Värdemängden för agent_runs.agent_type, spegel av check-villkoret i
# migration 025. Bor här, inte i respektive lagring, av ett skäl som kostade
# ett halvår att lära sig: villkoret fanns bara i Postgres, MemoryStorage tog
# emot vad som helst, testerna körde mot minnet och var gröna — samtidigt som
# ingen enda leads-körning sparades i produktion.
AGENT_RUN_TYPES = (
    "support",
    "leads",
    "leads_research",
    "leads_outreach",
    "demo",
    # Bokföringsagenten (migration 045). Lades till HÄR och i migrationen i
    # samma ändring — det är hela läxan ovan.
    "bookkeeping",
)


# Värdemängden för bk_underlag.status, spegel av check-villkoret i migration
# 045. Bor här av exakt samma skäl som AGENT_RUN_TYPES ovan — och `klar`/
# `granska_manuellt` är dessutom verifieringsgrindens två utgångar, så
# tests/bookkeeping/test_status_domain.py kontrollerar att de två listorna
# inte glidit isär.
BK_STATUSAR = ("granska_manuellt", "klar", "godkand")

BK_RIKTNINGAR = ("intakt", "kostnad")


class BkValideringsfel(ValueError):
    """Ett värde Postgres hade avvisat med check-violation.

    Kastas av BÅDA lagringarna via hjälparna nedan. Att minnet tar emot mer än
    databasen är hela mekanismen bakom "ingen leads-körning har någonsin
    sparats" — se AGENT_RUN_TYPES.
    """


def kontrollera_bk_status(status: str) -> None:
    if status not in BK_STATUSAR:
        raise BkValideringsfel(
            f"status={status!r} finns inte i bk_underlag check-villkoret {BK_STATUSAR}."
        )


def kontrollera_bk_riktning(riktning: str | None) -> None:
    if riktning is not None and riktning not in BK_RIKTNINGAR:
        raise BkValideringsfel(
            f"riktning={riktning!r} finns inte i bk_underlag check-villkoret {BK_RIKTNINGAR}."
        )


#: Kolumnernas skala i migration 045. `momssats` är numeric(5,4), resten
#: numeric(14,2).
BK_SKALA: dict[str, Decimal] = {"momssats": Decimal("0.0001")}
BK_SKALA_STANDARD = Decimal("0.01")


def bk_belopp(varde: object, falt: str) -> Decimal | None:
    """None förblir None; allt annat måste vara Decimal — kvantiserat till
    kolumnens skala.

    Float avvisas HÄR också och inte bara i math.py: kolumnen är
    numeric(14,2), och asyncpg skickar en float som en approximation utan att
    säga till. Ett öre som försvinner i lagringen är osynligt tills en
    periodrapport inte går ihop.

    KVANTISERINGEN är inte kosmetik. Postgres lagrar `numeric(5,4)` och ger
    tillbaka `Decimal("0.2500")`; MemoryStorage gav `Decimal("0.25")` — samma
    värde, olika STRÄNG. API:t serialiserar belopp som strängar (se `_kr` i
    app/api/bookkeeping.py), så vyn fick "0.06" i varje test och "0.0600" i
    drift. Den skillnaden hann bli en bugg: momsetiketten räknade ut 60 %
    i stället för 6 %, och bara mot Postgres.
    """
    if varde is None:
        return None
    if isinstance(varde, Decimal):
        return varde.quantize(BK_SKALA.get(falt, BK_SKALA_STANDARD))
    raise BkValideringsfel(
        f"{falt}: {type(varde).__name__} går inte att lagra som numeric — skicka Decimal."
    )


def bk_datum(varde: object) -> date | None:
    """Normaliserar inmatat datum till `date`. Accepterar även ISO-sträng.

    Finns för att BÅDA lagringarna ska ta emot samma sak. Utgången är däremot
    alltid en ISO-STRÄNG i båda — Postgres via `_row`, som isoformatar allt med
    `.isoformat()`, och minnet genom att lagra strängen direkt. Utan den
    symmetrin hade en vy som fungerade mot minnet fått ett `date`-objekt där
    produktionen ger en sträng, och felet hade dykt upp först i drift.
    """
    if varde is None:
        return None
    if isinstance(varde, datetime):
        return varde.date()
    if isinstance(varde, date):
        return varde
    if isinstance(varde, str):
        try:
            return date.fromisoformat(varde)
        except ValueError as orsak:
            raise BkValideringsfel(f"datum: {varde!r} är inte ISO-format") from orsak
    raise BkValideringsfel(f"datum: {type(varde).__name__} är inte ett datum")


def kontrollera_bk_balans(rader: list[dict[str, Any]]) -> None:
    """Debet minus kredit måste vara noll.

    Villkoret finns i BÅDA lagringarna och inte bara i grinden: ett obalanserat
    verifikat som ändå hamnar i databasen gör varje senare periodrapport fel,
    och då är felet en rad i en tabell i stället för ett verdikt i en kö.
    """
    if not rader:
        raise BkValideringsfel("verifikat utan rader kan inte balansera")
    debet = sum((bk_belopp(r.get("debet"), "debet") or Decimal(0) for r in rader), Decimal(0))
    kredit = sum((bk_belopp(r.get("kredit"), "kredit") or Decimal(0) for r in rader), Decimal(0))
    if debet != kredit:
        raise BkValideringsfel(
            f"verifikatet balanserar inte: debet {debet} mot kredit {kredit}"
        )


#: Vilka mätvärden i `weekly_analytics` som har en källa i databasen.
#:
#: Bor här och inte i respektive lagring av exakt samma skäl som
#: AGENT_RUN_TYPES ovan: två kopior blir förr eller senare två svar, och det
#: ena hade sagt att vi mäter något vi inte mäter.
#:
#: `meetings` är false eftersom ingenting skriver bokade möten. Autonominivån
#: `meeting` i leads/autonomy.py saknar produktionsanropare, och `public.meetings`
#: är workspace-skopad i Next-appens schema — inte något backenden når per tenant.
#: Demons analysvy har visat en möteskolumn sedan start; den kolumnen har aldrig
#: haft en motsvarighet i drift. Sätt det här till true samma dag en rad skrivs,
#: inte innan.
ANALYTICS_COVERAGE: dict[str, bool] = {
    "sent": True,
    "replies": True,
    "leads_runs": True,
    "support_runs": True,
    "tickets": True,
    "escalated": True,
    "resolved": True,
    "meetings": False,
}


# Framåtriktade statusövergångar, som i referensrepot (forward-only).
STATUS_ORDER = ["open", "in_progress", "escalated", "resolved", "closed"]


def status_transition_allowed(current: str, new: str) -> bool:
    try:
        return STATUS_ORDER.index(new) >= STATUS_ORDER.index(current)
    except ValueError:
        return False
