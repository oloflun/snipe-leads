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
    "policy_url",
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



#: Fälten `spara_bedomning` får skriva på prospektraden (Iris-bedömningen,
#: migration 024/031/079). En lista, delad av båda lagringarna, så att de
#: aldrig kan glida isär.
BEDOMNINGSFALT = (
    # Migration 083 (plan del C): lägesbeskrivning, signaler, och telefonen
    # ur källmaterialet när registret (081) saknade den.
    "lagesbeskrivning",
    "signaler",
    "contact_phone",
    "niva",
    "score_total",
    "score_breakdown",
    "motivering",
    "profil_version",
    "jev",
    "icp_fit",
    "qualified",
    "disqualifiers",
    "status",
    "ort",
    "postnr",
    "anstallda",
    # Migration 094 (plan 2026-10-05, fas 3): PageSpeed och bildbedömningen.
    "webbrevision",
)

#: Fälten Processa om får skriva på en listrad (app/leads/omprova.py).
LISTRAD_UPPDATERBARA = (
    "website", "contact_name", "contact_role", "contact_email", "contact_phone", "contact_level", "signal_detalj",
    # Migration 108 och 110: Processa om (leads/omprova.py) och kopplingen
    # till radens prospekt.
    "orgnr", "webbniva", "webbrevision", "kallor", "processad_at", "prospect_id",
)
#: Kolumnerna ovan som är jsonb och skrivs som JSON.
LISTRAD_JSONB = ("webbrevision", "kallor")


class Storage(Protocol):
    name: str

    # -- Tenants (administrativa; kräver master-nyckel i API-lagret) --------

    async def create_tenant(self, *, slug: str, name: str) -> dict[str, Any]: ...

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None: ...

    async def list_tenants(self) -> list[dict[str, Any]]: ...

    async def set_tenant_active(self, tenant_id: str, *, active: bool) -> dict[str, Any] | None:
        """Slår på eller av kundens konto. None när tenanten inte finns.

        Avstängning är trial-konverteringens manuella väg (beslut 2026-09-20):
        `validate_api_key` avvisar nycklar för en inaktiv tenant, så alla tre
        agenterna, webben och den publika chatten låses ute i samma ögonblick.
        Ingenting raderas — en återaktivering öppnar allt igen.
        """
        ...

    async def set_tenant_status(self, tenant_id: str, *, status: str) -> dict[str, Any] | None:
        """Sätter kontots läge: 'aktiv', 'pausad' eller 'avstangd' (migration 080).

        `active` hålls i synk i SAMMA skrivning (active = status == 'aktiv') —
        spärren och etiketten får aldrig säga olika saker. 'pausad' och
        'avstangd' låser ute lika hårt; skillnaden är avsikten, och den läses
        av adminytan och händelseloggen, inte av någon grind.
        """
        ...

    async def get_tenant_products(self, tenant_id: str) -> list[str] | None:
        """Paketet ur den kopplade arbetsytans `workspaces.products`.

        `None` betyder "ingen kopplad arbetsyta" (configfil-kunder), inte
        "inga produkter" — anropare ska behandla None som okänt och inte
        stänga något på det. Se produktgrinden i app/api/deps.py.
        """
        ...

    # -- Inkorgar -----------------------------------------------------------

    async def list_mailboxes(self, tenant_id: str) -> list[dict[str, Any]]: ...

    # -- Spegel och flytt (migration 085, plan del E) ------------------------

    async def spegel_info(self) -> dict[str, Any] | None:
        """Markören spegelskriptet sätter (scripts/railway_seed_dev.py,
        tabellen public.mirror_meta): {environment, seeded_at} i en spegel,
        None i main och i minneslagret. admin_flytt.importera vägrar i en
        spegel; panelen Flytta till main renderas bara i en."""
        ...

    async def logga_flytt(self, tenant_id: str, *, typ: str, ref_id: str, resultat: str) -> None:
        """Kvitto per flyttad rad (dev_flytt_ko). resultat: 'ok' | 'fel'."""
        ...

    async def list_flytt(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """Senaste flyttarna, nyast först."""
        ...

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
        """Kopplar (eller kopplar OM) en inkorg — självbetjäningsvägen.
        `syfte` (migration 084): support | leads | bada — styr klassningen.

        Upsert på (tenant_id, address): en kund som skriver in ett nytt
        app-lösenord för samma adress ska uppdatera raden, inte samla
        dubbletter. `secret_enc` är Fernet-krypterat i API-lagret INNAN det
        når hit (migration 077) — den här metoden får aldrig se klartext."""
        ...

    async def delete_mailbox(self, tenant_id: str, mailbox_id: str) -> bool:
        """Kopplar ur en inkorg. True när en rad faktiskt togs bort."""
        ...

    async def touch_mailbox_sync(
        self, tenant_id: str, mailbox_id: str, *, last_error: str | None
    ) -> None:
        """Stämplar ett synkförsök: last_sync_at = nu, last_error = utfallet.

        Kolumnerna fanns i fyra månader utan att någon kodväg skrev dem —
        kundens 'senaste synk' stod tom för evigt och ett fel lösenord var
        helt tyst (upptäckt 2026-09-07 när en bevakning läste null och drog
        slutsatsen att pollern var död, fast den hade hämtat mail)."""
        ...

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
        author: str | None = None,
    ) -> dict[str, Any]:
        """`author` (migration 066): 'customer', 'agent' eller 'human'. None
        lämnar kolumnen tom, vilket läses som inbound = kunden, outbound =
        agenten — beteendet för varje rad före migrationen."""
        ...

    async def get_messages(
        self, tenant_id: str, conversation_id: str
    ) -> list[dict[str, Any]]: ...

    # -- Trial (migration 074) ----------------------------------------------

    async def list_trial_paminnelse_kandidater(self, *, idag: date) -> list[dict[str, Any]]:
        """Arbetsytor vars trial går ut om exakt 7 eller exakt 1 dagar.

        En kandidat är en riktig arbetsyta (inte demo) utan signerat avtal
        vars påminnelse av den typen inte redan är loggad. Raden bär
        `workspace_id`, `name`, `trial_slut`, `email` (ägarens) och
        `dagar_kvar` (7 eller 1). Läses OSKOPAT — plattformssvep, inte
        kunddata; se app/jobs/trial_paminnare.py.
        """
        ...

    async def spara_trial_paminnelse(
        self, *, workspace_id: str, typ: str, skickad_till: str
    ) -> bool:
        """Loggar en skickad påminnelse. False när typen redan var loggad.

        Skickning sker FÖRE loggning (hellre en dubblett efter en krasch än
        en tyst utebliven påminnelse); unikheten per (workspace, typ) är det
        som gör sveparen omkörningsbar.
        """
        ...

    async def list_customer_emails(self, tenant_id: str) -> list[str]:
        """Tenantens egna slutkunders mejladresser (ss_customer_identifiers).

        Underlaget till send_guard regel 3:s `egna_kunder`: en befintlig kund
        ska inte få ett kallmejl om det den redan köpt. Fram till 2026-09-20
        skickade schemaläggaren en tom mängd hit — spärren fanns i guarden men
        hade aldrig data att döma mot.
        """
        ...

    async def find_customer(self, tenant_id: str, *, email: str) -> dict[str, Any] | None:
        """Kunden med den här e-postidentifieraren, eller None. Skapar ALDRIG.

        Skild från find_or_create_customer av ett skäl: chattfönstrets
        pollning är anonym, och en läsväg som skapar en kundrad per okänt
        sessions-id vore en skrivväg för vem som helst med en slumpgenerator.
        """
        ...

    # -- Samtalsläge (migration 066) ----------------------------------------
    #
    # En rad per (tenant, kund). Saknas raden gäller standardläget — läsaren
    # får alltid en fullständig dict, aldrig None, så att agenten inte
    # behöver särskilja "ny kund" från "kund utan läge".

    async def get_chat_state(self, tenant_id: str, customer_id: str) -> dict[str, Any]: ...

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
        """Upsert av hela läget. `overlamnad_at` sätts av lagringen när
        `lage` går från 'agent' till 'overlamnad' (och står kvar vid en
        uppdatering av ett redan överlämnat samtal); den nollas när läget går
        tillbaka till 'agent'. `updated_at` sätts vid varje anrop — det är
        klockan överlämningens giltighetstid räknas från."""
        ...

    async def list_chat_handovers(
        self, tenant_id: str, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Överlämnade samtal, senast uppdaterade först, med kundens namn och
        det överlämnade ärendets ämne/kategori/is_test. Portalens Chattar-vy."""
        ...

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

    async def delete_kb_article(self, tenant_id: str, artikel_id: str) -> bool:
        """Tar bort EN artikel i tenantens egen bas. False om den inte finns
        (eller tillhör någon annan — RLS gör de två fallen omöjliga att skilja
        åt, och det ska de vara). Kräver migration 069 (delete-grant)."""
        ...

    async def kb_utan_vektor(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """Artiklar som sparades medan inbäddningarna var trasiga (2026-09-12
        till 2026-10-06), äldst först. Omindexeringen fyller på dem."""
        ...

    async def satt_kb_vektor(self, tenant_id: str, artikel_id: str, embedding: list[float]) -> None: ...

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

    async def get_send_queue_item(self, tenant_id: str, item_id: str) -> dict[str, Any] | None:
        """En send_queue-post, eller None om den inte finns hos tenanten."""
        ...

    async def senaste_ko_for_trad(self, tenant_id: str, thread_id: str) -> dict[str, Any] | None:
        """Trådens senaste send_queue-post (vilken status som helst), eller None.
        Körningens utkastvy läser status per lead härifrån."""
        ...

    async def update_outreach_message_text(
        self, tenant_id: str, message_id: str, *, subject: str, body: str
    ) -> None:
        """Skriver om ett EJ skickat utkasts ämne och text (granskarens
        redigering). Ett skickat meddelande rörs aldrig."""
        ...

    async def get_pending_outreach_message(
        self, tenant_id: str, thread_id: str
    ) -> dict[str, Any] | None:
        """Det äldsta outbound-meddelandet i tråden utan sent_at."""
        ...

    async def mark_outreach_message_sent(self, tenant_id: str, message_id: str, sent_at: Any) -> None: ...

    async def list_skickade(self, tenant_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        """Skickade leadsmejl (outbound, sent_at satt) över alla trådar, senast
        först, med bolag och mottagare — fliken Skickat i Iris-leads
        (Sebbe 2026-10-07). `last_inbound_at` säger om bolaget svarat."""
        ...

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
        outbound_sent_count, first_outbound_sent_at, last_outbound_sent_at,
        last_inbound_at och has_pending_item (köad/väntande post eller osänt,
        icke-kasserat utkast), plus prospektets `origin` för automationsreglerna
        per typ och `prospect_status`/`arkiverad_at` (ett avslutat eller
        arkiverat lead följs inte upp). Aggregaten räknas i lagringen, varje
        rad en gång (count distinct: två joinade tabeller multiplicerade annars
        varandra) — policyn (NÄR en uppföljning är förfallen) bor i
        app/leads/follow_up_generator.py och är testbar utan databas."""
        ...

    async def utkast_lagen(
        self, tenant_id: str, *, med_text: bool = False, prospect_id: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """Underlaget för utkaststatusen per lead (app/leads/utkaststatus.py),
        nycklat på prospect_id, i EN fråga för hela tenanten (eller ett lead).

        Per lead: thread_id, skickat_at (senaste skickade utgående),
        antal_skickade, och trådens SENASTE köpost (queue_item_id, ko_status,
        gate_checks, scheduled_at; ordnad på created_at). `med_text` lägger
        till det aktuella meddelandet (message_id, subject, body): det väntande
        (osänt, icke-kasserat, senast skapade) i första hand, annars det
        senaste. Ett lead utan tråd saknas i svaret."""
        ...

    async def cancel_pending_sends(self, tenant_id: str, thread_id: str) -> int:
        """Ställer in trådens köade/väntande send_queue-poster. Körs när ett
        svar kommit in: det som låg i kön skrevs till någon som inte hade
        svarat, och den premissen gäller inte längre. Trådens osända utkast
        kasseras samtidigt (migration 107), så att inget av dem väljs som
        väntande text igen. Returnerar antalet inställda poster."""
        ...

    async def list_pending_sends(self, tenant_id: str, thread_id: str) -> list[dict[str, Any]]:
        """Trådens köade/väntande send_queue-poster (queued, awaiting_review),
        äldst först. Köningen läser dem så att en tråd aldrig bär två väntande
        utkast (2026-10-08)."""
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
        self, tenant_id: str, foretagsnyckel: str, *, utom_trad: str | None = None
    ) -> Any | None:
        """När bolaget senast kontaktades, oavsett kontaktperson. Nyckeln är
        FÖRETAGET — ett bolag som byter kontaktperson ska inte kunna få ett
        nytt kallmejl dagen efter.

        `utom_trad`: leadets egen tråd räknas inte. 90-dagarsspärren gäller ett
        NYTT kallmejl; en uppföljning eller ett svarsutkast i samma samtal
        stoppades annars av samtalets eget första mejl (2026-10-08)."""
        ...

    # -- G11: segmentaggregatet (den enda avsiktliga tenantgränsöverskridningen) --

    # -- Webbpoolen (migration 108, INV-SEC-008): plattformstabell utan tenant --

    async def webbpool_hamta(self, domaner: list[str]) -> dict[str, dict[str, Any]]:
        """Poolens rader för domänerna, nycklade på domän."""
        ...

    async def webbpool_spara(self, rad: dict[str, Any]) -> None:
        """Upsert på domän. Bara bolagsnivå (webbpool.POOLFALT); ett befintligt
        värde skrivs aldrig över med None."""
        ...

    async def webbpool_ofordelade(
        self, mottagare: str, *, lan: list[str], nivaer: list[str], limit: int = 200
    ) -> list[dict[str, Any]]:
        """Bedömda rader i länen och nivåerna som mottagaren inte fått."""
        ...

    async def webbpool_markera_fordelad(self, mottagare: str, domaner: list[str], list_id: str | None) -> None: ...

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
        # Fas 7 (migration 101): systemlagrens text, {hash: text}, ur
        # RunTrace.lagertexter(). Läggs EN gång per unik hash i prompt_lager
        # (insert … on conflict do nothing); step_log bär bara hashen. Ett fel
        # där fäller aldrig loggningen av körningen.
        prompt_lager: dict[str, str] | None = None,
        # Kolumnen finns sedan migration 025 men skrevs aldrig. Insynens kedja
        # per bolag (GET /api/admin/prospects/{id}/kedja) hittar körningarna
        # genom den.
        prospect_id: str | None = None,
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

    async def get_prompt_lager(self, hashar: list[str]) -> dict[str, str]:
        """Lagertexterna för de givna hasharna (prompt_lager, migration 101).
        Saknade hashar saknas i svaret — en äldre körning, eller en text vars
        skrivning föll."""
        ...

    # -- Leads-jobbens liggare (INV-JOB-002) --------------------------------

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
        """Skriver/uppdaterar EN rad i leads_job_ledger (migration 059, 080).

        `korning`, `error` och `is_test` (080, INV-JOB-003) skrivs bara när de
        ges — None lämnar kolumnen orörd, så ett statusbyte aldrig raderar
        ett tillstånd som skrevs steget innan.

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

    async def list_prospekt_i_research(self, tenant_id: str) -> set[str]:
        """Prospekten vars researchjobb står i queued eller processing i
        liggaren (scope research/research_and_draft; ett rent utkastjobb är
        ingen research). Underlaget för den härledda statusen "Research
        pågår" i GET /api/leads/prospects (Sebbe 2026-10-07): härledd i
        stället för lagrad, så att en process som dör aldrig lämnar ett bolag
        fast i den — städaren failar jobbet och bolaget står som Ny igen."""
        ...

    async def list_leads_korningar(self, tenant_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Tenantens körningar (liggarens batch- och listrader), nyast
        först: job_id, status, scope, is_test, created_at, updated_at,
        completed_at, error, korning (INV-JOB-003). Prospektjobben (scope
        research/research_and_draft/draft) är inte körningar och tas inte
        med — de är körningens barn och står i `korning.jobs`."""
        ...

    async def get_sidcache(self, tenant_id: str, url: str) -> dict[str, Any] | None:
        """Sidcachen (migration 093, app/leads/sidhamtning.py): {innehall, fel, hamtad_at}."""
        ...

    async def put_sidcache(self, tenant_id: str, url: str, *, innehall: str | None, fel: str | None) -> None:
        """Skriver över raden för (kund, url) och stämplar hamtad_at = nu."""
        ...

    async def set_korning_styrning(self, tenant_id: str, job_id: str, styrning: str | None) -> bool:
        """Sätter `korning.styrning` ('paus' | 'avbruten' | None) atomiskt på
        en pågående Iris-körning. Bara den här metoden skriver fältet:
        set_leads_job_status bevarar det, så motorns helskrivning av
        tillståndet (som kan ha läst före pausen) aldrig nollar den. False när
        körningen inte finns, inte är en pågående batch eller redan är klar."""
        ...

    async def get_leads_korning(self, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        """EN körning med samma fält som list_leads_korningar, eller None."""
        ...

    async def sum_leads_tokens(self, tenant_id: str, *, hours: int = 24) -> int:
        """Summan tokens_in + tokens_out för leads-agenttyperna
        ('leads_research', 'leads_outreach', 'leads_svar', 'leads_followup')
        de senaste `hours` timmarna — budgetgrindens fråga
        (app/leads/budget.py). Testkörningar räknas MED: de kostar samma
        pengar hos leverantören som skarpa körningar."""
        ...

    async def sum_support_tokens(self, tenant_id: str, *, hours: int = 24) -> int:
        """Supportens motsvarighet till sum_leads_tokens: summan för
        SUPPORT_BUDGET_AGENT_TYPES de senaste `hours` timmarna — frågan
        bakom supportbudgeten (app/budget.py). Testkörningar räknas MED,
        av samma skäl."""
        ...

    async def daily_support_usage(
        self, tenant_id: str, *, days: int = 30
    ) -> list[dict[str, Any]]:
        """Journalens dagliga serie (GET /api/usage): en rad per dag med
        körningar för SUPPORT_BUDGET_AGENT_TYPES, nyaste först. Fält per rad:
        `datum` (ISO-dag), `korningar`, `korningar_test`, `tokens_in`,
        `tokens_out`. Dagar utan körningar utelämnas — en tom dag är ingen
        rad, inte en nollrad (till skillnad från weekly_analytics, som är en
        kurva och behöver sina hål ifyllda)."""
        ...

    # -- Leadslistor (tillägget 'leadlists', migration 060) -----------------
    #
    # Metoderna står i PROTOKOLLET av samma skäl som log_agent_run: en
    # signatur som bara finns i ett lager är så halvårsbuggar föds.

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
        """`kalla`, `kallistor`, `kontaktfilter` (migration 082): en kombinerad
        lista bär sina källistor och filtret som användes, så bygget går att
        granska i efterhand. 'sok' för allt som byggs av en sökning."""
        ...

    async def set_lead_list_status(
        self, tenant_id: str, list_id: str, *, status: str, felorsak: str | None = None
    ) -> None:
        """'bestalld' | 'byggs' | 'klar' | 'fel' — spegel av check-villkoret
        i migration 060 (minnet ska kasta där Postgres kastar)."""
        ...

    async def list_lead_lists(self, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """Nyaste först, med `item_count` per rad."""
        ...

    async def saljlista_fyll_pa(self, tenant_id: str, rader: list[dict[str, Any]]) -> int:
        """Skriver färdiga rader till arbetsytans säljlista (public.saljlista,
        migration 103/105): nycklarna foretagsnamn, orgnr, kontaktperson,
        kontaktnummer, kontaktmail, anteckningar. Dedupliklerar mot befintliga
        rader på orgnr-siffror eller bolagsnamn och returnerar antalet
        inlagda. Finns ingen arbetsyta för tenanten skrivs ingenting (0)."""
        ...

    async def get_lead_list(self, tenant_id: str, list_id: str) -> dict[str, Any] | None: ...

    async def add_lead_list_item(
        self, tenant_id: str, *, list_id: str, **falt: Any
    ) -> dict[str, Any]:
        """En rad i listan. `item_typ` defaultar till 'bolag' — MVP:n skriver
        aldrig 'privatperson' (juridiskt beslut, se migration 060)."""
        ...

    async def list_lead_list_items(
        self, tenant_id: str, list_id: str, *, med_flyttade: bool = False
    ) -> list[dict[str, Any]]:
        """Listans rader utom de som flyttats till Iris eller ringlistan
        (`signal='flyttad'`): ett bolag visas på ett ställe (2026-10-08).
        `med_flyttade` för åtgärder på EN rad som redan kan ha flyttats."""
        ...

    async def uppdatera_listrad(self, tenant_id: str, item_id: str, falt: dict[str, Any]) -> None:
        """Processa om (2026-10-08): kontaktsökningens fynd skrivs på raden.
        Bara LISTRAD_UPPDATERBARA; övriga nycklar ignoreras."""
        ...

    async def satt_listprocessering(self, tenant_id: str, list_id: str, processering: dict[str, Any] | None) -> None:
        """Förloppet för listans Processa om / Skapa utkast (migration 110)."""
        ...

    async def listkopplade_prospekt(self, tenant_id: str) -> set[str]:
        """Prospekt som är en listrads bakgrundspost (migration 110). Iris-
        tabellen visar dem inte: bolaget står i sin lista."""
        ...

    async def markera_listrad_flyttad(self, tenant_id: str, item_id: str, *, signal_detalj: str) -> None:
        """Raden blev ett prospekt. Den raderas aldrig (Antons beslut
        2026-10-07) men döljs: `signal='flyttad'` och var den hamnade."""
        ...

    async def spara_listutkast(
        self, tenant_id: str, item_id: str, utkast: dict[str, Any] | None
    ) -> None:
        """Sätter (eller nollar) listradens utkast (migration 106,
        app/leads/listutkast.py)."""
        ...

    async def lista_upptagna_bolag(self, tenant_id: str) -> list[dict[str, Any]]:
        """`company_name` och `orgnr` för varje bolag kunden redan har: alla
        prospekt och alla rader i alla leadslistor (CRM-kunder inräknade).
        Iris och listbygget utesluter dem (app/leads/upptagna.py)."""
        ...

    async def rensa_lead_list_items(self, tenant_id: str, list_id: str) -> int:
        """Tar bort EN listas rader. Returnerar antal borttagna.

        För listor som inte blev klara: en misslyckad lista ska inte visa en
        halv tabell (uppmätt 2026-09-13: tre skräprader under en lista som
        stod i 'byggs' i dagar)."""
        ...

    async def delete_lead_list(self, tenant_id: str, list_id: str) -> bool:
        """Raderar EN lista; raderna följer med (on delete cascade, 060).
        Bara kundens eller adminens uttryckliga Ta bort lista, och flytten av
        en lista till en annan kund, går hit. False om listan inte fanns."""
        ...

    async def stada_hangande_leadsjobb(
        self, tenant_id: str, *, aldre_an_minuter: int, utom: list[str] | None = None
    ) -> list[str]:
        """Markerar liggarrader i queued/processing med updated_at äldre än
        `aldre_an_minuter` som failed (pausade körningar undantagna). `utom` är job_id som körs i den här
        processen och aldrig ska städas. Returnerar de städade job_id:na.
        Se app/jobs/stadare.py."""
        ...

    async def stada_hangande_leadslistor(
        self,
        tenant_id: str,
        *,
        aldre_an_minuter: int,
        felorsak: str,
        utom: list[str] | None = None,
    ) -> list[str]:
        """Markerar listor i bestalld/byggs äldre än `aldre_an_minuter` som
        'fel' med `felorsak`, och tar bort deras rader i samma svep.
        Returnerar de städade list_id:na. Se app/jobs/stadare.py."""
        ...

    async def support_oversikt_underlag(
        self, tenant_id: str, *, sedan: str, is_test: bool | None
    ) -> dict[str, Any]:
        """Råraderna bakom Kundtjänst › Översikt (app/support_oversikt.py).

        Returnerar `{"mejl": [...], "korningar": {...}, "kb_artiklar": int}`.
        Varje mejl: `id, received_at, status, category, escalate,
        kb_traffar (int | None), forsta_svar (iso | None)`, för supportmejl
        mottagna från och med `sedan`. Larm, leads och dolda räknas inte.
        `forsta_svar` är första `auto_sent`/`approved_and_sent` i
        beslutsloggen. `korningar` summerar periodens supportkörningar
        (utan is_test): `antal, tokens_in, tokens_out, cache, modell`.

        Aggregeringen sker i Python och inte här, så att Postgres och minnet
        inte kan räkna olika.
        """
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
        gate_checks: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Skapar meddelandet (sent_at=NULL) OCH send_queue-raden i samma
        operation — det finns ingen kodväg som skapar det ena utan det andra.

        `status` avgörs av kundens autonominivå (app/leads/autonomy.py):
        'queued' släpps till schemaläggaren, 'awaiting_review' väntar på att
        en människa godkänner. Default är 'queued' för att inte ändra
        beteendet för anropare som inte känner till nivån.

        `gate_checks` blir köpostens första grindanteckning. Köningen lägger
        `held` där när text- eller stilkontrollen tvingat granskning, så att
        granskaren ser varför (utkaststatus.harled läser den)."""
        ...

    async def tilldela_erbjudande(self, tenant_id: str, thread_id: str, *, nyckel: str) -> str:
        """Kopplar tråden till kundens erbjudande `nyckel` (app/leads/erbjudanden.py):
        get-or-create en `offers`-rad per kund och nyckel (name = nyckeln) och
        sätt `outreach_threads.offer_id`. Returnerar offer-id:t."""
        ...

    async def erbjudande_utfall(self, tenant_id: str) -> list[dict[str, Any]]:
        """Utfallet per erbjudande, räknat på trådar med `offer_id`: en rad per
        nyckel med `utkast` (trådar med ett utgående meddelande), `skickade`
        (med ett skickat), och bland de skickade `svar`, `positiva` och `moten`.

        Härledningen, eftersom svarsklassen inte sparas i en egen kolumn:
        app/leads/svar.py är den enda kodvägen som sätter prospektets status
        med källan 'kod' till replied/meeting/lost/suppressed (statusloggen,
        migration 086), och 'meeting' med 'kod' är just klassen positivt. Ett
        möte är ett samtalsutfall 'mote' (lead_samtal), en manuell flytt till
        'meeting' eller status 'won'. Bara loggrader från trådens start räknas."""
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

    async def list_prospects(self, tenant_id: str, *, limit: int = 500) -> list[dict[str, Any]]: ...

    async def arkivera_prospekt(
        self, tenant_id: str, prospect_ids: list[str], *, arkivera: bool
    ) -> list[str]:
        """Sätter (arkivera=True) eller nollar `arkiverad_at` (migration 107).
        Ett arkiverat lead är dolt i Iris-listan men behåller historiken och
        står kvar i uteslutningsmängden. Returnerar id:na som fanns."""
        ...

    async def radera_prospekt(self, tenant_id: str, prospect_ids: list[str]) -> dict[str, list[str]]:
        """Raderar de leads som ALDRIG kontaktats (inget utgående meddelande
        med sent_at), i en transaktion. {"raderade": [...], "kontaktade": [...]}:
        ett kontaktat lead raderas aldrig — utskicksloggen bär 90-dagars-
        spärren och avregistreringarna, så det arkiveras i stället. Trådar,
        utkast, köposter och Suite-raderna följer med (on delete cascade)."""
        ...

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
        adress. Se `app/agent/leads_agent.py::_uppgradera_kontakt`.

        `status_kalla` (migration 086): när `status` ändrar prospektets status
        skrivs en rad i `prospect_status_logg` med `kalla` — här och bara här,
        så att svarshanteringen, sändningen och PATCH loggas likadant."""
        ...

    # -- Leads Suite (migration 086) -----------------------------------------

    async def add_lead_note(self, tenant_id: str, *, prospect_id: str, text: str) -> dict[str, Any]: ...

    async def list_lead_notes(self, tenant_id: str, prospect_id: str) -> list[dict[str, Any]]:
        """Äldst först."""
        ...

    async def add_lead_task(
        self, tenant_id: str, *, prospect_id: str, titel: str, forfaller: str | None
    ) -> dict[str, Any]: ...

    async def update_lead_task(
        self, tenant_id: str, task_id: str, *, klar: bool | None = None
    ) -> dict[str, Any] | None:
        """`klar_at` sätts när `klar` blir True och nollas när den blir False."""
        ...

    async def list_lead_tasks(
        self, tenant_id: str, *, prospect_id: str | None = None, bara_oppna: bool = False
    ) -> list[dict[str, Any]]:
        """Förfallodag stigande, uppgifter utan förfallodag sist."""
        ...

    async def list_status_logg(
        self, tenant_id: str, *, prospect_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Nyast först."""
        ...

    # -- Samtal (migration 107, app/leads/samtal.py) ---------------------------

    async def add_lead_samtal(
        self,
        tenant_id: str,
        *,
        prospect_id: str,
        utfall: str,
        aterkom_datum: str | None,
        anteckning: str | None,
    ) -> dict[str, Any]: ...

    async def list_lead_samtal(
        self, tenant_id: str, *, prospect_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Äldst först. Utan `prospect_id`: hela tenantens samtal."""
        ...

    async def list_lead_views(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def create_lead_view(
        self, tenant_id: str, *, namn: str, filter: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def delete_lead_view(self, tenant_id: str, view_id: str) -> bool: ...

    async def spara_bedomning(
        self, tenant_id: str, prospect_id: str, *, bedomning: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Iris-bedömningen (migration 079 + 024 + 031) i ETT anrop:
        niva, score_total, score_breakdown, motivering, profil_version, jev,
        icp_fit, qualified, disqualifiers, status — plus ort/postnr/anstallda
        när researchen hittade dem. Nycklar som saknas i `bedomning` rörs inte.
        Se app/leads/bedomning.py."""
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
        automatutskick: bool = False,
        mailbox_id: str | None = None,
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
        inkludera_larm: bool = False,
        klass: str | None = None,
    ) -> list[dict[str, Any]]:
        """Utan statusfilter utesluts 'att_hantera' (migration 078) — utom
        när `inkludera_larm` är satt, vilket get_email-uppslag behöver.
        `klass` (migration 084): support | lead | ej_relaterat; None = alla.
        Utan klassfilter och utan statusfilter visas inte heller 'lead' och
        'ej_relaterat' — de bor i leads-inkorgen respektive Dolda."""
        ...

    async def get_email(self, tenant_id: str, email_id: str) -> dict[str, Any] | None: ...

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
        """`hanterad` styr `hanterad_at` (migration 071): True stämplar (om
        inte redan stämplad), False nollar, None rör inte. Oberoende av
        `status` — se migrationens motivering. `klass`/`klass_kalla`
        (migration 084) skrivs bara när de ges."""
        ...

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
        offertforfragan: bool = False,
        utbildningsintresse: bool = False,
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

    async def get_global_instructions(self, agent_type: str = "alla") -> dict[str, Any] | None:
        """Den aktiva globala instruktionen för `agent_type` (migration 099:
        'alla', 'support' eller 'leads'), eller None.

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
        agent_type: str = "alla",
        feedback: str = "",
    ) -> dict[str, Any]:
        """Ny version för `agent_type`. Avaktiverar den föregående i SAMMA transaktion — det
        partiella unika indexet tillåter bara en aktiv rad, så två steg utan
        transaktion hade kunnat lämna noll aktiva efter ett avbrott."""
        ...

    async def list_global_instructions(
        self, *, limit: int = 20, agent_type: str = "alla", med_text: bool = False
    ) -> list[dict[str, Any]]:
        """Historiken för `agent_type`, nyast först. `med_text` tar med
        dokumentet och feedbacken (för återställning och visning). Driftverktyg: svarar på 'vad stod det när
        den där körningen gjordes?'."""
        ...

    async def get_global_instruction(self, instruktion_id: str) -> dict[str, Any] | None:
        """En version, aktiv eller inte, med hela texten. För återställning."""
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
        # Insynens kedja per bolag (Fas 7). None = alla.
        prospect_id: str | None = None,
        # Bara listans fält (SAMMANDRAG_FALT) — utan input, output och
        # step_log, som är 99 % av radens vikt. Adminlistorna läser inget mer.
        sammandrag: bool = False,
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
        """Ett underlag, med de fält avläsningen faktiskt hittade.

        `granskning`/`granskningsstatus` (migration 096) bär kvittohanterarens
        hela avläsning enligt grundprompten: varje fält med säkerhet och källa,
        flaggorna, kontrollräkningarna och statusen ur avsnitt 9.2. De platta
        kolumnerna ovan är det verifikatet och summorna räknar på.

        Kvittofälten (migration 063): `kalla` säger VAR kvittot kom ifrån
        (uppladdning eller mejl), mejl_*-fälten bär avsändare och ämne när
        källan är ett mejl, och `valuta`/`belopp_original` bär ett utländskt
        belopp som INTE räknats om — SEK-kolumnen lämnas då tom och grinden
        flaggar raden.

        Fälten är `None`-bara med flit: ett underlag där grinden fällt SKA gå
        att spara med hål i, annars finns ingen granskningskö att fylla.
        Grinden, inte databasen, avgör om det får bli en periodrapport.
        """
        ...

    async def markera_kvittomejl_last(
        self, tenant_id: str, fingeravtryck: str, *, klass: str
    ) -> None:
        """Ett mejl kvittohanteraren läst och som INTE gav något underlag
        (migration 096). Utan minnet hade samma nyhetsbrev lästs av modellen
        vid varje skanning. Idempotent."""
        ...

    async def ar_kvittomejl_last(self, tenant_id: str, fingeravtryck: str) -> bool: ...

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
        betalstatus: str | None = None,
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
        nummer: str | None = None,
        datum: date,
        text: str,
        rader: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Verifikatet med sina konteringsrader, i EN transaktion.

        Rader och huvud i samma skrivning: ett verifikat utan rader balanserar
        inte, och ett halvskrivet verifikat är precis den sortens post som får
        en periodrapport att se rimlig ut och vara fel.

        `nummer=None` betyder "nästa lediga i serien", räknat av LAGRINGEN i
        själva skrivningen. Anropare ska inte räkna numret själva ur en
        listlängd — två samtidiga anrop läser då samma längd och skriver samma
        nummer (granskningsfynd snipe-a4y). Postgres backar upp med ett unikt
        index per (tenant, serie, nummer) och försöker om vid kollision.
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
    # Anropen utanför stegmotorn — bolagssökningen, Jev-triagen och
    # profilkompileringen (migration 101, app/agentcore/insyn.samla_anrop).
    "leads_underlag",
)

#: Agenttyperna som räknas mot leads-budgeten (sum_leads_tokens /
#: app/leads/budget.py). Delmängd av AGENT_RUN_TYPES — bor här av samma skäl
#: som resten: EN lista, speglad av båda lagringarna, aldrig två svar.
LEADS_BUDGET_AGENT_TYPES = ("leads_research", "leads_outreach", "leads_svar", "leads_followup")

#: Agenttyperna som räknas mot supportbudgeten (sum_support_tokens /
#: app/budget.py). Bara 'support' i dag: chatten och kanalerna loggar sina
#: körningar så, medan e-postpipelinens fristående triage-anrop inte loggas
#: som agent_runs alls — grinden prövas ändå i processorn.
SUPPORT_BUDGET_AGENT_TYPES = ("support",)


# Värdemängden för bk_underlag.status, spegel av check-villkoret i migration
# 045. Bor här av exakt samma skäl som AGENT_RUN_TYPES ovan — och `klar`/
# `granska_manuellt` är dessutom verifieringsgrindens två utgångar, så
# tests/bookkeeping/test_status_domain.py kontrollerar att de två listorna
# inte glidit isär.
BK_STATUSAR = ("granska_manuellt", "klar", "godkand")

BK_RIKTNINGAR = ("intakt", "kostnad")

#: Spegel av check-villkoret i migration 062. Samma mekanism som BK_RIKTNINGAR:
#: minnet får aldrig ta emot mer än databasen, annars är sviten grön medan
#: Postgres fäller på check-violation vid första riktiga skrivning.
BK_BETALSTATUSAR = ("betald", "obetald")


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


def kontrollera_bk_betalstatus(betalstatus: str | None) -> None:
    if betalstatus is not None and betalstatus not in BK_BETALSTATUSAR:
        raise BkValideringsfel(
            f"betalstatus={betalstatus!r} finns inte i bk_underlag "
            f"check-villkoret {BK_BETALSTATUSAR}."
        )


#: Kvittots väg in (migration 063). Spegel av check-villkoret i migrationen.
BK_KALLOR: tuple[str, ...] = ("uppladdning", "mejl")


def kontrollera_bk_kalla(kalla: str) -> None:
    if kalla not in BK_KALLOR:
        raise BkValideringsfel(
            f"kalla={kalla!r} finns inte i bk_underlag check-villkoret {BK_KALLOR}."
        )


#: Kvittohanterarens status ur grundpromptens avsnitt 9.2 (migration 096).
#: Spegel av check-villkoret; `kvitton/granskning.GRANSKNINGSSTATUSAR` ska
#: vara samma lista (testas i tests/kvitton/test_granskning.py).
BK_GRANSKNINGSSTATUSAR: tuple[str, ...] = (
    "KLAR_FÖR_GRANSKNING",
    "BEHÖVER_GRANSKNING",
    "PRIORITERAD_GRANSKNING",
    "KRÄVER_MANUELL_HÄMTNING",
)


def kontrollera_bk_granskningsstatus(status: str | None) -> None:
    if status is not None and status not in BK_GRANSKNINGSSTATUSAR:
        raise BkValideringsfel(
            f"granskningsstatus={status!r} finns inte i bk_underlag "
            f"check-villkoret {BK_GRANSKNINGSSTATUSAR}."
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
    "new_leads": True,
    "meetings": False,
}


#: ss_messages.author (migration 066). None är också giltigt — en äldre rad.
MEDDELANDE_AVSANDARE = ("customer", "agent", "human")

#: ss_chat_state.lage (migration 066).
SAMTALSLAGEN = ("agent", "overlamnad")


def standard_samtalslage(tenant_id: str, customer_id: str) -> dict[str, Any]:
    """Läget för en kund utan rad: agenten svarar, inget räknat, inget erbjudet.

    Delad av båda lagringarna så att "ingen rad" betyder exakt samma dict i
    sviten som i drift — samma skäl som bk-valideringarna ovan bor här."""
    return {
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "lage": "agent",
        "misslyckade_i_rad": 0,
        "erbjod_manniska": False,
        "overlamnad_orsak": None,
        "overlamnad_ticket_id": None,
        "overlamnad_at": None,
        "sprak": None,
        "updated_at": None,
    }


def kontrollera_samtalslage(lage: str, misslyckade_i_rad: int) -> None:
    """Samma villkor som tabellens check-constraints, körda FÖRE skrivningen
    i båda lagringarna — annars säger minnet ja där Postgres säger nej."""
    if lage not in SAMTALSLAGEN:
        raise ValueError(f"Okänt samtalsläge: {lage!r}")
    if misslyckade_i_rad < 0:
        raise ValueError("misslyckade_i_rad kan inte vara negativ.")


# Framåtriktade statusövergångar, som i referensrepot (forward-only).
STATUS_ORDER = ["open", "in_progress", "escalated", "resolved", "closed"]


def status_transition_allowed(current: str, new: str) -> bool:
    try:
        return STATUS_ORDER.index(new) >= STATUS_ORDER.index(current)
    except ValueError:
        return False
