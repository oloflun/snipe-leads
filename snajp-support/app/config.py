"""Central konfiguration för Snajp-Support-tjänsten."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default-tenanten (Nordlys Handel) — samma fasta UUID som i 003_snajp_multitenant.sql.
DEFAULT_TENANT_ID = "00000000-0000-4000-a000-000000000001"
DEFAULT_TENANT_SLUG = "nordlys-handel"
DEFAULT_TENANT_NAME = "Nordlys Handel"

# A2b/Del F steg 12: Snajp som sin egen tenant — mk:churn-prevention är
# direkt tillämplig på Snajp självt (Snajp ÄR SaaS med prenumerationer),
# vilket gör den till ett testfall innan den blir policygenerator åt andra.
# Onboarding (product-marketing.md, customer-research, retentionsplaybook)
# är ett live-steg, inte något som körs vid migrationstillfället.
SNAJP_TENANT_ID = "00000000-0000-4000-a000-000000000002"
SNAJP_TENANT_SLUG = "snajp"
SNAJP_TENANT_NAME = "Snajp"

# G8: den publika, oautentiserade demon. Egen tenant, egen (tom/generisk) KB
# — delar ingenting med Nordlys Handel eller någon betalande kund. Skiljer
# sig från SNAJP_DEMO_API_KEY (som kräver en nyckel och pekar på Nordlys
# Handels fulla, seedade KB) — G8-demon kräver ingen nyckel alls.
PUBLIC_DEMO_TENANT_ID = "00000000-0000-4000-a000-000000000099"
PUBLIC_DEMO_TENANT_SLUG = "public-demo"
PUBLIC_DEMO_TENANT_NAME = "Snajp — offentlig demo"

# G8 rate-tak: "en publik LLM-endpoint utan tak är en räkning som skriver
# sig själv." Två oberoende tak — vilket som helst som slår i stoppar anropet.
PUBLIC_DEMO_MAX_PER_SESSION = 15
PUBLIC_DEMO_SESSION_WINDOW_SECONDS = 30 * 60
PUBLIC_DEMO_MAX_PER_IP = 30
PUBLIC_DEMO_IP_WINDOW_SECONDS = 60 * 60

# MÅSTE matcha check-villkoret ss_knowledge_base_category_check i databasen.
# Låg de isär klassificerade agenten ärenden som databasen sedan vägrade spara.
# Live-uppsättningen innehåller garanti och utbildning men inte konto.
CATEGORIES = (
    "teknisk_support",
    "garanti",
    "leverans",
    "utbildning",
    "retur_reklamation",
    "betalning",
    "orderstatus",
    "ovrigt",
)

CATEGORY_LABELS = {
    "teknisk_support": "Teknisk support",
    "garanti": "Garanti",
    "leverans": "Leverans",
    "utbildning": "Utbildning",
    "retur_reklamation": "Retur & reklamation",
    "betalning": "Betalning",
    "orderstatus": "Orderstatus",
    "ovrigt": "Övrigt",
}

# Miljöer som bär eller speglar riktig kunddata. `development` står med MED
# FLIT: Railway-miljön development är en spegel av produktionen (se CLAUDE.md),
# alltså riktiga kunders mejladresser och ärenden. En "det är bara dev"-
# invändning gäller inte här.
#
# Modulnivå och inte klassattribut: pydantic-settings tolkar varje oannoterat
# klassattribut som ett fält och vägrar bygga modellen.
MILJOER_MED_KUNDDATA = ("main", "production", "prod", "development", "dev")

# De providernamn koden faktiskt kan hantera. Varje post här MÅSTE ha en
# nyckel i `active_llm_key` och en bas-URL i `agent/llm._resolve_base_url` —
# annars är den inte stödd, den ser bara stödd ut.
KANDA_PROVIDERS = ("openai", "deepseek", "gemini")

# Regler per fack: auto = skicka direkt, draft = kräver godkännande, escalate = alltid människa.
DEFAULT_CATEGORY_RULES = {category: "draft" for category in CATEGORIES}


class Settings(BaseSettings):
    # ABSOLUT sökväg, inte ".env" — en relativ sökväg löses mot cwd, vilket
    # gjorde att nycklarna tyst försvann så fort tjänsten/ett skript kördes
    # från någon annan katalog än snajp-support/ (upptäckt när
    # scripts/run_live_tests.py kördes från repo-roten och ALLA live-anrop
    # föll på "Missing credentials").
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Vilken driftmiljö processen kör i. Sätts av Railway (RAILWAY_ENVIRONMENT_NAME
    # sätts automatiskt av plattformen); ENVIRONMENT finns för lokal körning och
    # för den dag vi inte kör på Railway. Tom = okänd miljö, vilket behandlas som
    # UTVECKLING — se `har_riktig_kunddata` för varför det är rätt håll att falla.
    environment: str = ""
    railway_environment_name: str = ""

    # LLM-provider: "openai" eller "deepseek" (OpenAI-kompatibel endpoint).
    #
    # SE `llm_provider_fault` NEDAN INNAN DU ÄNDRAR DEFAULTEN. DeepSeek är
    # tillåten bara mot syntetisk data; i main och development vägrar tjänsten
    # starta med den. Beslutet är dokumenterat i CLAUDE.md.
    llm_provider: str = "openai"
    llm_base_url: str = ""  # tom => härleds från provider (se agent/llm.py)
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    # Gemini (Google AI Studio, OpenAI-kompatibel endpoint) driver vision-
    # sidovagnen och embeddings — vald för gratisnivån, se scripts/keys.py.
    gemini_api_key: str = ""
    embedding_api_key: str = ""  # tom => faller tillbaka på gemini_api_key
    model: str = "gpt-4o-mini"
    embedding_model: str = "gemini-embedding-001"
    #: MÅSTE stämma med kolumnen `ss_knowledge_base.embedding`, som är
    #: `vector(1536)` sedan migration 002.
    #:
    #: `gemini-embedding-001` returnerar 3072 värden om man inte ber om något
    #: annat, och en 3072-vektor går inte att skriva i en 1536-kolumn. Det hade
    #: inte upptäckts förrän nu: embeddings har ALDRIG lyckats i den här
    #: kodbasen (Gemini-API:t var inte aktiverat på Google-projektet), så noll
    #: av 159 artiklar bär en vektor och krocken har aldrig prövats.
    #:
    #: Följden om värdet tas bort: `POST /api/kb` börjar svara 500 i stället
    #: för att spara artikeln utan vektor. Alltså byts en fungerande
    #: försämring mot ett avbrott — precis det `embed_text` finns för att
    #: undvika.
    embedding_dimensions: int = 1536
    # G9: vision-sidovagn. deepseek-v4-flash saknar dokumenterat bildstöd, så
    # bilder beskrivs separat (Gemini, gratisnivå) och matas in som text i
    # DeepSeek-loopen. Bilden lagras aldrig efter beskrivningen.
    vision_model: str = "gemini-3.6-flash"

    # DeepSeek v4 kör "thinking mode" som DEFAULT — modellen producerar
    # reasoning_content före sitt svar, vilket kostar output-tokens och latens.
    #
    # GLOBAL DEFAULT: "disabled". Beslut 2026-08-07 efter skarp jämförelse
    # (docs/THINKING_MODE_COMPARISON.md, 66 anrop): identiska klassificerings-
    # och eskaleringsbeslut i båda lägena, 11x fler tokens och 6x längre
    # latens med thinking PÅ (130-209s/ärende — odugligt i livechatt).
    # Enskilda playbook-steg kan override:a detta (PlaybookStep.thinking) —
    # se app/agent/support_playbook.py, där cs:customer-escalation medvetet
    # kör med thinking PÅ trots den här defaulten.
    #
    # Leads-flödet HAR INGET BESLUT ÄNNU. Mailbaserat => ingen tidspress,
    # kvalitet är prioritet över kostnad. Playbook-stegen i
    # app/leads/*_playbook.py lämnas därför utan override tills en fullständig
    # jämförelse av VARJE delmoment i research+outreach är klar. Ändra inte
    # den globala defaulten för att "lösa" leads — testa och besluta separat.
    thinking_mode: str = "disabled"

    # Fas B research (G4). Tomt => research-verktyget vägrar med ett tydligt
    # fel i stället för att krascha eller tyst hoppa över skrapningen.
    scrapegraphai_api_key: str = ""
    database_url: str = ""
    redis_url: str = ""
    snajp_master_api_key: str = "snajp_master_dev_key_change_me"
    snajp_demo_api_key: str = "snajp_demo_2f8c1a9e4b7d"

    # Email-pipeline
    inbox_poll_seconds: int = 0  # 0 = ingen bakgrundspolling (mock triggas manuellt)

    # Leads send_queue-schemaläggare (Del J). Samma mönster som
    # inbox_poll_seconds: 0 = av (ingen bakgrundstask), sätts explicit i
    # produktion. Håller test/dev-uppstart fri från överraskande bakgrundsjobb.
    send_queue_poll_seconds: int = 0
    auto_send_min_confidence: float = 0.75
    imap_host: str = ""  # t.ex. imap.gmail.com eller outlook.office365.com
    imap_user: str = ""
    imap_password: str = ""  # Gmail: app-lösenord; Outlook: app-lösenord/IMAP-auth
    imap_folder: str = "INBOX"

    # Publik bas-URL för länkar som hamnar i utgående mejl (idag bara
    # avregistreringslänken). MÅSTE peka på Next-appen, inte på det här API:t —
    # det är Next som renderar /avregistrera/<token>.
    #
    # Tom => `app/leads/utskicksfot.py` kan inte bygga en fungerande länk, och
    # då blockerar send_guard regel 2 utskicket. Det är rätt utfall: ett
    # kallmejl med en trasig avregistreringslänk är värre än inget kallmejl.
    publik_bas_url: str = ""

    # Internlarm: SMTP-uppgifterna för snajpsupport@gmail.com. ETT konto för
    # HELA plattformen — det här är larm till OSS, inte kundutskick, och har
    # ingenting med per-tenant-avsändare att göra (se app/notifications/).
    #
    # Lösenordet är INTE kontolösenordet. Ett Gmail med tvåstegsverifiering kan
    # inte logga in på SMTP med det; det kräver ett app-specifikt lösenord.
    # Sätts i Railway av en människa, samma sorts post som OPENAI_API_KEY i
    # docs/JURIDIK_ATGARDER.md.
    #
    # Ligger HÄR och inte i en `os.getenv` inne i modulen, och det är inte
    # kosmetika: pydantic-settings läser snajp-support/.env utan att exportera
    # något till os.environ, så en direktläsning hade sett värdena i Railway
    # men aldrig lokalt. Tomt => larmvägen är av, och modulen loggar i stället.
    internlarm_smtp_anvandare: str = ""
    internlarm_smtp_losenord: str = ""

    # CORS: kommaseparerade origins som får anropa API:t direkt från en
    # webbläsare. Tom = av, vilket räcker för vår egen frontend — Next-proxyn
    # anropar backenden server-side, så webbläsaren träffar aldrig den här
    # tjänsten. Behövs den dag en kund vill anropa API:t från sin egen webbapp.
    allowed_origins: str = ""

    # AVSIKTLIGHETSGRIND — inte en säkerhetsmekanism. Se scripts/unlock_skills.py.
    #
    # Nyckeln hindrar ingen angripare: vem som helst med repo-write kan redigera
    # agent-core/skills/ direkt. Vad den hindrar är att ett MISSTAG eller en
    # AUTONOM AGENTKÖRNING regenererar manifestet eller publicerar skills till
    # databasen, eftersom värdet bara finns i snajp-support/.env på en enda
    # maskin och aldrig i Render/Vercel. Skriv aldrig om den här kommentaren
    # till något som låter som access control.
    snajp_skill_unlock_key: str = ""

    # "filesystem" | "db" — varifrån agent-core/skills/ läses (se agentcore/registry.py).
    # DEFAULT filesystem i ALL miljö. DB-spegeln är en granskningspost över vilken
    # text en agent_runs-rad producerades ur, inte en uppdateringskanal: kan DB:n
    # leverera text containern inte har på disk är git bara källa till sanning i
    # intentionen. render.yaml ska aldrig sätta SKILL_SOURCE.
    skill_source: str = "filesystem"

    @model_validator(mode="after")
    def _default_model_for_provider(self) -> "Settings":
        """Undvik footgun: ett gpt-modellnamn mot en icke-OpenAI-endpoint.

        DeepSeek och Gemini svarar båda 404 på "gpt-4o-mini" — ett fel som
        syns först vid första riktiga anropet, alltså hos en kund. `MODEL`
        får fortfarande sätta något annat; det här gäller bara när defaulten
        lämnats orörd.
        """
        if self.model.startswith("gpt-"):
            # 1M kontext, 384K output, $0.14/$0.28 per 1M token — se plan-dokumentet.
            if self.llm_provider == "deepseek":
                self.model = "deepseek-v4-flash"
            # Samma modellnamn som vision-sidovagnen redan använder mot samma
            # endpoint (se vision_model ovan) — alltså ett namn som är prövat
            # i den här kodbasen, inte ett gissat.
            elif self.llm_provider == "gemini":
                self.model = self.vision_model
        return self

    def active_llm_key(self) -> str:
        """Nyckeln som hör till den valda providern.

        VARFÖR EN KARTA OCH INTE EN IF-KEDJA MED FALLBACK: den tidigare
        versionen slutade med `return self.openai_api_key`, alltså returnerade
        den OpenAI-nyckeln för VARJE värde som inte var "deepseek". Ett
        felstavat eller okänt providernamn gav då en tom nyckel, och en tom
        nyckel är simuleringsläge — tjänsten startade, rapporterade sig frisk
        och slutade tyst använda AI.

        Det hände skarpt 2026-08-24: LLM_PROVIDER sattes till "gemini", ett
        värde koden inte kände till, och development svarade
        `mode: simulation` med regelmotorn i stället för agenten. Ingen
        deploy föll, ingenting larmade.

        Nu är okända värden ett FEL (se llm_provider_fault), och den här
        funktionen svarar tomt bara för en provider som saknar sin nyckel.
        """
        return {
            "openai": self.openai_api_key,
            "deepseek": self.deepseek_api_key,
            "gemini": self.gemini_api_key,
        }.get(self.llm_provider, "")

    def aktiv_miljo(self) -> str:
        """Miljönamnet, normaliserat. Tom sträng = okänd."""
        return (self.environment or self.railway_environment_name or "").strip().lower()

    def har_riktig_kunddata(self) -> bool:
        """Om den här processen kan nå riktiga personuppgifter.

        En OKÄND miljö räknas som utveckling och inte som produktion. Det ser
        ut som fel håll att falla, men är det inte: den enda konsekvensen av
        ett falskt negativt är att en lokal körning tillåter DeepSeek mot en
        databas som ändå är tom (`scripts/lokal_stack.py`). Ett falskt positivt
        hade i stället stoppat varje lokal utvecklingskörning, och en spärr som
        står i vägen dagligen är en spärr någon kommenterar bort.

        Det som faktiskt skyddar produktionen är att Railway ALLTID sätter
        RAILWAY_ENVIRONMENT_NAME. Miljönamnet är alltså aldrig okänt där.
        """
        return self.aktiv_miljo() in MILJOER_MED_KUNDDATA

    def llm_provider_fault(self) -> str | None:
        """Varför den valda LLM-providern inte får användas här, eller None.

        VARFÖR SPÄRREN FINNS: DeepSeek behandlar det som skickas till modellen
        i Kina. Allt som går genom agenten är kundens kundmejl — namn,
        adresser, ärendetext — och en tredjelandsöverföring dit kräver SCC,
        en överföringskonsekvensbedömning och ett uttryckligt villkor i
        PUB-avtalet. Inget av det finns 2026-08-24.

        VARFÖR DEN KRASCHAR I STÄLLET FÖR ATT VARNA: en varning i en logg som
        ingen läser är ingen spärr. Det fel den här spärren finns för att
        fånga — en felaktig `LLM_PROVIDER` i en Railway-miljö — ger annars en
        tjänst som ser fullt frisk ut medan varje ärende skickas utomlands.
        Ett dött bygge upptäcks inom minuter; en tyst överföring upptäcks vid
        en tillsyn.

        DeepSeek får fortfarande köras lokalt och i testsviten, mot
        MemoryStorage och syntetiska fixtures. Det är där den hör hemma.

        Vill vi ta tillbaka DeepSeek i drift är det ett AVTALSBESLUT, inte ett
        kodbeslut: SCC, TIA, PUB-villkor och information till kunden. Ändra
        inte den här funktionen för att komma runt det.
        """
        if self.llm_provider not in KANDA_PROVIDERS:
            return (
                f"LLM_PROVIDER={self.llm_provider!r} är inte ett providernamn "
                f"koden känner till. Välj ett av: {', '.join(KANDA_PROVIDERS)}. "
                f"Utan den här kontrollen hade tjänsten startat med en tom "
                f"nyckel och tyst gått ner i simuleringsläge — den hade svarat "
                f"kunder med regelmotorn i stället för med agenten, och "
                f"ingenting hade larmat."
            )

        if self.llm_provider == "deepseek" and self.har_riktig_kunddata():
            return (
                f"LLM_PROVIDER=deepseek är inte tillåtet i miljön "
                f"'{self.aktiv_miljo()}'. Den miljön bär eller speglar riktig "
                f"kunddata, och DeepSeek behandlar prompten i Kina utan att vi "
                f"har SCC, överföringsbedömning eller PUB-villkor på plats. "
                f"Sätt LLM_PROVIDER=openai och se till att OPENAI_API_KEY är "
                f"satt på BÅDA tjänsterna (web och api)."
            )
        return None

    def llm_key_fault(self) -> str | None:
        """Varför nyckeln inte går att använda, eller None.

        Ett API-nyckelvärde går i HTTP-huvudet `Authorization: Bearer <nyckel>`,
        och huvudvärden är per definition ASCII. En nyckel med ett tecken över
        127 kraschar därför inte hos leverantören utan INNE i http-klienten,
        långt efter att tjänsten rapporterat sig frisk.

        Det hände skarpt: /health/ready svarade "LLM-nyckel hittad — riktig
        agent aktiv", och första riktiga körningen föll på
        `'ascii' codec can't encode character 'à' in position 7` — position 7
        är första tecknet efter "Bearer ". Trovärdigt men fel, alltså samma
        klass av fel som migration 029 fick städa upp.
        """
        key = self.active_llm_key() or ""
        if not key:
            return None  # ingen nyckel alls är simuleringsläge, inte ett fel
        bad = next((i for i, ch in enumerate(key) if ord(ch) > 127), None)
        if bad is not None:
            return (
                f"LLM-nyckeln innehåller ett tecken utanför ASCII (position {bad}). "
                f"Den kan inte skickas i ett Authorization-huvud och varje "
                f"agentanrop kommer att falla. Sätt om nyckeln."
            )
        return None

    def embedding_faults(self) -> list[str]:
        """Vad som gör embeddings oanvändbara just nu. Tom lista = inget känt fel.

        Embeddings är en EGEN kedja: annan leverantör, annan nyckel, annan
        modell. `mode: live` mäter LLM-nyckeln och säger ingenting om den här —
        och två gånger nu har kedjan varit helt trasig medan hälsokontrollen
        rapporterat allt grönt:

          * Gemini-API:t var inte aktiverat på Google-projektet → 403, och noll
            av 159 KB-artiklar fick en vektor.
          * `EMBEDDING_MODEL` stod på `text-embedding-3-small` — ett OpenAI-namn
            — mot Geminis endpoint → 404.

        Kontrollen läser NAMN och nyckel, den ringer aldrig leverantören. En
        hälsokontroll som kostar pengar per pollning blir avstängd, och då mäter
        den ingenting alls.

        Att sakna nyckel är INTE ett fel här: fulltext-fallbacken är en giltig
        driftform. Det som rapporteras är konfiguration som ser rätt ut men inte
        kan fungera.
        """
        fel: list[str] = []
        key = self.embedding_api_key or self.gemini_api_key
        if not key:
            return fel  # medveten fulltext-drift, inte ett fel

        # Modellnamnet måste höra till leverantören nyckeln pekar på. Gemini
        # svarar 404 på ett OpenAI-namn, och felet syns först när någon skriver
        # en KB-artikel.
        if self.embedding_model.startswith("text-embedding-"):
            fel.append(
                f"EMBEDDING_MODEL={self.embedding_model} är ett OpenAI-namn, men "
                "embeddings går mot Gemini. Varje anrop svarar 404 och "
                "kunskapsbasen sparas utan vektorer."
            )

        bad = next((i for i, ch in enumerate(key) if ord(ch) > 127), None)
        if bad is not None:
            fel.append(
                f"Embeddings-nyckeln innehåller ett tecken utanför ASCII "
                f"(position {bad}) och kan inte skickas i ett huvud."
            )
        return fel

    def is_simulation(self) -> bool:
        # Samma platshållar-heuristik som app/api/email-studio/route.ts i Next-appen.
        key = self.active_llm_key() or ""
        # En trasig nyckel räknas som ingen nyckel. Alternativet är att tjänsten
        # påstår sig vara live och faller på första riktiga anropet — ett läge
        # som ser friskt ut i varje kontroll utom den som kostar en kund.
        if self.llm_key_fault():
            return True
        return len(key) < 20 or "..." in key or "din-" in key


@lru_cache
def get_settings() -> Settings:
    return Settings()
