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

#: Kundregistrets skrivbara fält (migration 053). Listan bor HÄR och läses av
#: båda lagringarna och av API-schemat — tre kopior av en fältlista blir förr
#: eller senare tre olika listor, och det är exakt så agent_type-buggen
#: överlevde ett halvår.
KUNDDATA_FALT = (
    "orgnr",
    "faktureringsadress",
    "faktureringsmejl",
    "telefon",
    "foretagsadress",
    "kund_sedan",
    "avtal_signerat",
)

_KUNDDATA_DATUMFALT = ("kund_sedan", "avtal_signerat")


def normalisera_kunddata(falt: dict[str, Any]) -> dict[str, Any]:
    """Delad validering för kundregistret, körd av BÅDA lagringarna.

    Semantiken speglar agentprofilen: ett utelämnat fält rörs inte, en tom
    sträng nollställer. Datumfält parsas till `date` — en sträng som inte är
    ett ISO-datum ska falla HÄR, med fältnamnet i felet, inte som ett
    asyncpg-undantag halvvägs ner i en upsert.
    """
    resultat: dict[str, Any] = {}
    for namn, varde in falt.items():
        if namn not in KUNDDATA_FALT:
            raise ValueError(f"Okänt kunddatafält: {namn}")
        if varde is None:
            continue
        if namn in _KUNDDATA_DATUMFALT:
            text = str(varde).strip()
            if not text:
                resultat[namn] = None
                continue
            try:
                resultat[namn] = date.fromisoformat(text)
            except ValueError as fel:
                raise ValueError(
                    f"{namn} måste vara ett datum på formen ÅÅÅÅ-MM-DD."
                ) from fel
        else:
            text = str(varde).strip()
            resultat[namn] = text or None
    return resultat


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
    ) -> list[dict[str, Any]]:
        """Kundens ärenden, nyast först.

        VARJE post bär `conversation_id` — samtalet som hör till ärendet, eller
        None för ett ärende utan samtal. Fältet finns INTE i ss_tickets; det
        kommer ur en join i PostgresStorage och sätts explicit i MemoryStorage.

        Kravet står här för att det en gång bara stod i den ena lagringen:
        MemoryStorage satte fältet, Postgres gjorde det inte, och
        arbetsminne.alla_samtalsrader kastade KeyError i drift medan sviten var
        grön. INV-STORE-001 jämför signaturer, inte returformer — den fångar
        alltså inte den här sortens glidning. Läsare måste tåla None.
        """
        ...

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
        is_test: bool | None = None,
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

    # -- Agentens föreslagna lärdomar (självlärning, 2026-08-26) -------------
    #
    # Supportens cs:kb-article och leads _fanga_kunskap RÄKNADE UT lärdomar på
    # varje körning och kastade dem — utdatan fanns i step_log och ingenstans
    # annars. Förslagen persisteras nu, men skrivs ALDRIG in i kundens
    # underlag av agenten själv: en människa godkänner (INV-LEARN-001). Det är
    # samma beslut som _fanga_kunskaps docstring pekar på — riskprofilen i att
    # agenten uppdaterar sitt eget facit är en annan, och den är inte tagen.

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
        """Sparar ett förslag. Returnerar None vid dubblett (samma dedupe_key
        med status 'ny' hos tenanten) — agenten som ser samma lucka i tio
        ärenden ska ge EN rad att granska, inte tio."""
        ...

    async def list_agent_suggestions(
        self, tenant_id: str, *, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]: ...

    async def update_agent_suggestion_status(
        self, tenant_id: str, suggestion_id: str, *, status: str
    ) -> dict[str, Any] | None:
        """Sätter 'godkand'/'avfard'. Returnerar raden, eller None om den inte
        finns — anroparen ska kunna svara 404 i stället för att låtsas."""
        ...

    async def save_agent_feedback(
        self,
        tenant_id: str,
        *,
        run_id: str,
        verdict: str,
        comment: str | None = None,
        corrected_output: str | None = None,
    ) -> dict[str, Any]:
        """Kundens dom över en körning (agent_feedback, migration 010).

        Tabellen har funnits sedan migration 010 utan en enda kodväg — samma
        felklass som instructions_md: schemat sa att signalen fanns, och
        ingenting samlade in den. Ett run_id som inte finns hos tenanten ska
        kasta (Postgres FK gör det; minnet speglar det uttryckligen), och
        verdict valideras mot check-villkoret i BÅDA lagringarna."""
        ...

    async def list_agent_feedback(
        self, tenant_id: str, *, verdict: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]: ...

    # -- Kundminne (customer_memory, migration 052) -------------------------
    #
    # mem0:s ADD-only-mönster: fakta läggs till, skrivs aldrig om av
    # pipelinen. Bär ENBART vad kunden själv uppgett (kontamineringsspärren —
    # se migrationens rubrik); injiceras alltid opålitligt-wrappad i
    # user-position.

    async def add_customer_facts(
        self, tenant_id: str, customer_id: str, *, fakta: list[str]
    ) -> int:
        """Sparar en lista korta faktarader. Returnerar antalet sparade.
        Tomma/blanka rader hoppas; dubbletter (exakt samma fakta för samma
        kund) hoppas — tio ärenden om samma telefon ska ge EN rad."""
        ...

    async def get_customer_facts(
        self, tenant_id: str, customer_id: str, *, limit: int = 12
    ) -> list[str]:
        """De senaste faktaraderna, äldst först i returen (läsordning för
        prompten). Limit är injektionstaket, inte lagringstaket."""
        ...

    # -- Golden eval-cases (agent_evals, migration 010 — första kodvägen
    #    2026-08-27). Langfuse/promptfoo-mönstret: golden-setet byggs ur
    #    VERKLIGA produktionsfel, och nedtummad feedback med rättad text blir
    #    automatiskt ett case (se api/leads.lamna_agent_feedback).

    async def save_eval_case(
        self,
        tenant_id: str,
        *,
        agent_type: str,
        input_text: str,
        expected_traits: dict[str, Any],
        approved_output: str | None = None,
    ) -> dict[str, Any]: ...

    async def list_eval_cases(
        self, tenant_id: str, *, agent_type: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]: ...

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

    async def find_outreach_thread(
        self, tenant_id: str, *, prospect_id: str
    ) -> dict[str, Any] | None:
        """LÄSDELEN av ensure_outreach_thread — för GET-vägar som inte får
        skapa. En sidladdning som letar efter ett befintligt utkast (Fas 5.5,
        GET /api/leads/prospects/{id}/utkast) ska inte lämna en tom tråd
        efter sig bara för att den tittade."""
        ...

    async def ensure_outreach_thread(
        self, tenant_id: str, *, prospect_id: str
    ) -> dict[str, Any]:
        """Tråden för ett prospekt — befintlig om en finns, annars skapad.

        Get-or-create och inte create: en tråd per prospekt är modellen
        (uppföljningar och svar hör till SAMMA samtal), och en andra tråd för
        samma prospekt hade delat historiken i två så att sekvensräkningen —
        den som avgör om ett mejl går ut utan granskning — börjar om från noll.

        Metoden fanns inte förrän 2026-08-26: `queue_outreach_message` skrev
        mot ett thread_id som INGEN kodväg någonsin skapade. MemoryStorage
        saknar FK-kontroll och släppte igenom det, så sviten var grön medan
        Postgres hade fällt första riktiga köningen på foreign key-villkoret.
        """
        ...

    async def record_inbound_reply(
        self, tenant_id: str, *, thread_id: str, body: str
    ) -> dict[str, Any]:
        """Ett inkommande prospektsvar: raden i outreach_messages plus
        last_inbound_at på tråden. De två skrivs ihop — ett svar som syns i
        listan men inte stoppar uppföljningsgeneratorn (som läser
        last_inbound_at) hade gett en uppföljning till någon som redan svarat."""
        ...

    async def list_outreach_threads(self, tenant_id: str) -> list[dict[str, Any]]:
        """Alla trådar med de aggregat uppföljningssvepet dömer på:
        outbound_sent_count, last_outbound_sent_at, last_inbound_at och
        has_pending_item (köad/väntande post eller osänt utkast). Aggregaten
        räknas i lagringen — policyn (NÄR en uppföljning är förfallen) bor i
        app/leads/follow_up_generator.py och är testbar utan databas."""
        ...

    async def cancel_pending_sends(self, tenant_id: str, thread_id: str) -> int:
        """Ställer in trådens köade/väntande send_queue-poster. Körs när ett
        svar kommit in: det som låg i kön skrevs till någon som inte hade
        svarat, och den premissen gäller inte längre. Returnerar antalet."""
        ...

    async def reschedule_pending_sends(
        self, tenant_id: str, thread_id: str, *, until: Any
    ) -> int:
        """Skjuter trådens köade poster till `until` (autosvar/semester).
        Returnerar antalet flyttade."""
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
        # Migration 055. "<provider>:<modell>" (settings.llm_provider +
        # settings.model), eller "svarscache" för en cacheträff som inte
        # körde någon modell alls. None för anropare som (ännu) inte skickar
        # det — kolumnen är nullable av samma skäl.
        model: str | None = None,
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

    # -- Leads-jobbens liggare (INV-JOB-002) --------------------------------

    async def set_leads_job_status(
        self,
        tenant_id: str,
        *,
        job_id: str,
        status: str,
        scope: str = "research",
        prospect_id: str | None = None,
    ) -> None:
        """Skriver/uppdaterar EN rad i leads_job_ledger (migration 059).

        Liggaren är sanningen om huruvida ett leads-jobb redan är färdigt.
        Redis-jobbposten (app/jobs/store.py) auto-failar efter 300 s och
        TTL:ar efter 3 600 s — vid ett XAUTOCLAIM-återtag efter en deploy
        såg vakten därför aldrig "completed" för köade batchjobb och körde
        om hela research+utkast-kedjan (uppmätt 2026-09-01: ~18 kr utan
        användarhandling). Vakten läser liggaren FÖRST; Postgres gäller vid
        konflikt med Redis. Metoden står i PROTOKOLLET av samma skäl som
        log_agent_run: en signatur som bara finns i ett lager är så
        halvårsbuggar föds."""
        ...

    async def get_leads_job_status(self, tenant_id: str, job_id: str) -> str | None:
        """Läser liggarens status för ETT jobb: 'queued' | 'processing' |
        'completed' | 'failed' — eller None om raden saknas (jobb från före
        migration 059, eller en annan miljös jobb)."""
        ...

    async def sum_leads_tokens(self, tenant_id: str, *, hours: int = 24) -> int:
        """Summan tokens_in + tokens_out för leads-agenttyperna
        ('leads_research', 'leads_outreach', 'leads_svar', 'leads_followup')
        de senaste `hours` timmarna — budgetgrindens fråga
        (app/leads/budget.py). Testkörningar räknas MED: de kostar samma
        pengar hos leverantören som skarpa körningar."""
        ...

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
        origin: str | None = None,
        orgnr: str | None = None,
        website: str | None = None,
        contact_email: str | None = None,
        contact_name: str | None = None,
        contact_role: str | None = None,
        contact_level: str | None = None,
        contact_form_url: str | None = None,
    ) -> dict[str, Any] | None:
        """Fas B:s bedömning (icp_fit, qualified, disqualifiers) landar här,
        migration 024. Innan den fanns räknades icp_fit ut av modellen och
        kastades bort — den gick inte att sortera, mäta eller motivera i
        efterhand.

        `origin` (Fas 3, §4) är den enda vägen `POST .../befordra` skriver:
        'test'/'example' → 'manual', efter att valideringen i
        `leads/befordran.py` godkänt bolaget.

        `contact_name`/`contact_role`/`contact_level`/`contact_form_url`
        (migration 058) är UPPGRADERINGSVägen för kontaktfältets
        fallback-trappa: Fas B:s per-prospekt research läser det redan
        skrapade källmaterialet och kan hitta en namngiven person där den
        breda `hitta_bolag()`-sökningen bara verifierade en rollbaserad
        adress. Se `app/agent/leads_agent.py::_uppgradera_kontakt`."""
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
        is_test: bool = False,
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
        is_test: bool | None = False,
    ) -> list[dict[str, Any]]: ...

    async def get_email(self, tenant_id: str, email_id: str) -> dict[str, Any] | None: ...

    async def update_email(
        self,
        tenant_id: str,
        email_id: str,
        *,
        status: str | None = None,
        ticket_id: str | None = None,
        is_test: bool | None = None,
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

    # -- Instruktionslagret (migration 049) ---------------------------------
    #
    # VÅR text, inte kundens. Går i SYSTEMposition. Kundskriven text (SOUL,
    # affärskontext, KB) ligger kvar i USERposition — se app/leads/soul.py för
    # varför den skillnaden är mekanismen och inte en försiktighetsåtgärd.

    async def get_global_instructions(self) -> dict[str, Any] | None:
        """Den aktiva globala instruktionen, eller None.

        None betyder "ingen har skrivit någon ännu" och är inte ett fel:
        app/agentcore/instruktioner.py faller då tillbaka på den incheckade
        agent-core/AGENTS.md, som är det beteende som gällde före 049.
        """
        ...

    async def save_global_instructions(
        self,
        *,
        ravtext: str,
        strukturerad_md: str,
        kalla: str = "ai",
        uppdaterad_av: str | None = None,
    ) -> dict[str, Any]:
        """Ny version. Avaktiverar den föregående i SAMMA transaktion — det
        partiella unika indexet tillåter bara en aktiv rad, så två steg utan
        transaktion hade kunnat lämna noll aktiva efter ett avbrott."""
        ...

    async def list_global_instructions(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Historiken, nyast först. Driftverktyg: svarar på 'vad stod det när
        den där körningen gjordes?'."""
        ...

    async def get_agent_config(self, tenant_id: str, *, agent_type: str) -> dict[str, Any]:
        """Hela raden ur agent_configs, eller defaultvärden om den saknas.

        Skild från get_agent_settings, som bara ger jsonb-kolumnen. De två
        hade kunnat vara en, men settings läses av varje leads-körning medan
        det här bara läses av admin och av prompten — och en bredare läsning i
        den heta vägen är inte gratis.
        """
        ...

    async def set_agent_instructions(
        self,
        tenant_id: str,
        *,
        agent_type: str,
        instructions_md: str,
        instructions_rav: str = "",
        tone: str | None = None,
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

    # -- Kundregister (migration 053, kräver master-nyckel) -----------------
    #
    # Samma åtkomstmodell som admin-läsningarna ovan: metoderna anropas
    # enbart från app/api/admin_kunddata.py bakom require_master_key, och
    # RLS-policyn i 053 släpper bara fram dem på en OSKOPAD anslutning.
    # Skrivsemantiken delas via normalisera_kunddata(): utelämnat fält rörs
    # inte, tom sträng nollställer.

    async def get_customer_details(self, tenant_id: str) -> dict[str, Any] | None:
        """Kundens registerrad, eller None när ingen skrivits ännu."""
        ...

    async def orgnr_for_tenant(self, tenant_id: str) -> str | None:
        """Tenantens EGET organisationsnummer, läsbart från en tenant-skopad körning.

        Skild från `get_customer_details` med flit: den läser hela
        kundregisterraden och skyddas av en RLS-policy som BARA släpper igenom
        en oskopad admin-anslutning (migration 053). En agentkörning har
        `app.tenant_id` satt och får därför noll rader därifrån — tyst.

        Den här metoden går via `orgnr_for_current_tenant()` (migration 056),
        som returnerar exakt ett fält för exakt den tenant som redan är
        inloggad. Se migrationens kommentar för varför den saknar parameter.
        """
        ...

    async def upsert_customer_details(
        self, tenant_id: str, falt: dict[str, Any]
    ) -> dict[str, Any]:
        """Skriver de fält som skickats med och returnerar hela raden."""
        ...

    async def list_customer_contacts(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def create_customer_contact(
        self,
        tenant_id: str,
        *,
        namn: str,
        roll: str | None = None,
        mejl: str | None = None,
        telefon: str | None = None,
    ) -> dict[str, Any]: ...

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
        """None när kontakten inte finns HOS DEN TENANTEN — ett id ur en annan
        kunds lista ska svara 404, inte uppdateras."""
        ...

    async def delete_customer_contact(self, tenant_id: str, contact_id: str) -> bool: ...

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

    async def get_bk_underlag_by_sha256(
        self, tenant_id: str, sha256: str
    ) -> dict[str, Any] | None:
        """Svaret på "har vi sett det här kvittot förut?" — hela skälet till
        att sha256 sparas, se noten ovan. Äldsta träffen om flera finns."""
        ...

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

    async def rensa_bk_period(
        self,
        tenant_id: str,
        *,
        fran: date | None = None,
        till: date | None = None,
    ) -> int:
        """Raderar underlagen i perioden och verifikaten som hänger på dem.

        URVALET ÄR SAMMA SOM `list_bk_underlag`, inte ett snävare. Ett underlag
        utan datum tas alltså MED, precis som listan tar med det — det är just
        de posterna grinden fällt, och en rensning som lämnar kvar det man ser
        i vyn är en knapp som ljuger om vad den gjorde.

        Verifikaten följer med. I Postgres via `on delete cascade` (migration
        045), i minnet för hand — och det är därför returvärdet räknar
        UNDERLAG och inget annat: talet ska betyda samma sak i båda
        lagringarna.

        Originalfilerna finns inte att radera; bara `sha256` sparades någonsin.
        """
        ...

    async def close(self) -> None: ...


# Värdemängden för agent_runs.agent_type, spegel av check-villkoret i
# migration 025. Bor här, inte i respektive lagring, av ett skäl som kostade
# ett halvår att lära sig: villkoret fanns bara i Postgres, MemoryStorage tog
# emot vad som helst, testerna körde mot minnet och var gröna — samtidigt som
# ingen enda leads-körning sparades i produktion.
# Värdemängden för agent_feedback.verdict, spegel av check-villkoret i
# migration 010. Samma regel som AGENT_RUN_TYPES nedan.
FEEDBACK_VERDICTS = ("good", "bad", "needs_review")

AGENT_RUN_TYPES = (
    "support",
    "leads",
    "leads_research",
    "leads_outreach",
    "demo",
    # Bokföringsagenten (migration 045). Lades till HÄR och i migrationen i
    # samma ändring — det är hela läxan ovan.
    "bookkeeping",
    # Svarshanteringen och uppföljningsgeneratorn (migration 051). Samma
    # regel: konstanten och migrationen i SAMMA ändring.
    "leads_svar",
    "leads_followup",
)

#: Agenttyperna som räknas mot leads-budgeten (sum_leads_tokens /
#: app/leads/budget.py). Delmängd av AGENT_RUN_TYPES — bor här av samma skäl
#: som resten: EN lista, speglad av båda lagringarna, aldrig två svar.
LEADS_BUDGET_AGENT_TYPES = ("leads_research", "leads_outreach", "leads_svar", "leads_followup")


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
