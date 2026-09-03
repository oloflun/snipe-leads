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


#: Värdnamn som betyder "databasen kör på den här maskinen". Bara de här räknas
#: som syntetisk data — se `Settings.har_riktig_kunddata`. Listan är kort med
#: flit: varje post är en adress som per definition inte kan vara en delad
#: produktionsdatabas.
_LOOPBACK = ("localhost", "127.0.0.1", "::1", "[::1]", "host.docker.internal")


def _vard_ur_dsn(database_url: str) -> str:
    """Värddelen ur en DSN, för felmeddelanden.

    ALDRIG hela DSN:en. Ett felmeddelande hamnar i en deploy-logg, och en
    logg är inte en hemlig plats — se läckagespärren i CLAUDE.md.
    """
    utan_schema = str(database_url or "").split("://", 1)[-1]
    myndighet = utan_schema.split("/", 1)[0]
    return myndighet.rsplit("@", 1)[-1].rsplit(":", 1)[0].strip() or "okänd värd"


def _ar_loopback(database_url: str) -> bool:
    """Om DSN:en pekar på den egna maskinen.

    Läser värddelen och inget annat. En DSN kan bära lösenord med `@` i, så
    värden tas efter SISTA `@` — annars hade ett lösenord med snabel-a kunnat
    få en produktionsdatabas att se ut som localhost, vilket är exakt fel
    riktning för en dataskyddsspärr att gissa åt.
    """
    utan_schema = str(database_url or "").split("://", 1)[-1]
    myndighet = utan_schema.split("/", 1)[0]
    vard = myndighet.rsplit("@", 1)[-1].rsplit(":", 1)[0].strip().lower()
    return vard in _LOOPBACK

# Modellnamn -> vilken provider namnet HÖR TILL. Bara entydiga prefix står här;
# ett namn som inte matchar något av dem släpps igenom, eftersom leverantörerna
# döper nya modeller utan att fråga oss och en för snäv lista hade blockerat
# giltig konfiguration.
#
# VARFÖR KONTROLLEN FINNS: `MODEL` stod kvar på "deepseek-v4-flash" när
# LLM_PROVIDER byttes till "gemini" 2026-08-24. Tjänsten startade, rapporterade
# `mode: live`, och svarade 404 på VARJE anrop — "models/deepseek-v4-flash is
# not found". Hälsokontrollen mäter att en nyckel finns, inte att modellen
# existerar hos den provider nyckeln pekar på, och den skillnaden kostade en
# hel eftermiddag första gången.
MODELLFAMILJER = {
    "gpt-": "openai",
    "o1-": "openai",
    "o3-": "openai",
    "o4-": "openai",
    "deepseek": "deepseek",
    "gemini": "gemini",
}


def provider_for_model(model: str) -> str | None:
    """Vilken provider ett modellnamn hör till, eller None om det inte går att säga."""
    namn = (model or "").strip().lower()
    for prefix, provider in MODELLFAMILJER.items():
        if namn.startswith(prefix):
            return provider
    return None

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
    # Fas R1 (bd snipe-lr7): antal worker-tasks som läser crm:jobb:chatt
    # (app/jobs/stream.py) PER PROCESS. Bara relevant när redis_url är satt
    # — utan Redis finns ingen ström att läsa, och app.state.chattstrom är
    # None (se app/main.py). Fler än 1 så en enskild långsam agentkörning
    # inte blockerar nästa chattmeddelande i kön.
    chat_workers: int = 2
    # Fas R4 (bd snipe-2xj): antal worker-tasks som läser crm:jobb:leads
    # (samma ChattStrom-klass som chatten, andra stream_key/group — se
    # app/jobs/stream.py) PER PROCESS. Default 1, inte 2 som chatten: ett
    # leads-jobb är ÅTTA LLM-anrop (research-steget, app/agent/leads_agent.py)
    # mot chattens sex-sju, och en batch kan innehålla upp till 50 prospekt
    # (LeadsBatchRequest.limit) — flera parallella workers hade kunnat
    # brännsprinta genom hela tenant-timkvoten på sekunder i stället för att
    # köa disciplinerat. Höjs bara efter att kvotmarginalen mätts i drift.
    leads_workers: int = 1
    # V2-kostnadsarbetet (2026-09-02): vilken leads-kedja som körs.
    # "v1" = niostegsresearchen + fyrstegsutkastet (dagens beteende).
    # "v2" = 1 research-anrop + 2 utkastanrop (RESEARCH_V2/OUTREACH_V2,
    # app/agent/leads_research_v2.py) — ~10x billigare per lead.
    # Default v1 tills scripts/benchmark_leads_kedja.py + 1–2 riktiga
    # Gemini-körningar godkänt kvaliteten; flippas då per miljö via env
    # LEADS_PIPELINE=v2, aldrig som kodändring före benchmarken.
    leads_pipeline: str = "v1"
    # Per-steg-modellval för V2-utkastet (beslut Sebbe 2026-09-02, vägen
    # till 0,10 kr/lead): utkast- och humanizerstegen i OUTREACH_V2 kör den
    # här modellen medan research behåller huvudmodellen. Uppmätt varför:
    # utkastfasens INPUT (skilltexterna) är 55 % av leadkostnaden och
    # okänslig för modellstyrka på ett annat sätt än research — texten som
    # ska skrivas är fem rader, regelverket står i prompten. Tom sträng =
    # ärv MODEL (ingen skillnad mot innan). Sätts per miljö via env
    # LEADS_DRAFT_MODEL, flippas ALDRIG i kod före domarbenchmark
    # (scripts/benchmark_leads_kedja.py, jämför utkastkvalitet V1 mot V2).
    leads_draft_model: str = ""
    # Humanizerns EGEN modell — skild från utkastets efter domarbenchmarken
    # 2026-09-02: lite-modellen på humanizersteget tappade å/ä/ö och
    # förlorade 3/4 blinda domar. Tom = ärv MODEL (huvudmodellen), vilket är
    # rätt läge tills en NY domarkörning bevisar annat. Se outreach_playbook.
    leads_humanizer_model: str = ""
    # Leads-budgeten (INV-JOB-002-arbetet, app/leads/budget.py): max summa
    # tokens_in+tokens_out per tenant och rullande 24 timmar över leads-
    # agenttyperna. Vid taket svarar körningsstarterna 429 i stället för att
    # köa fler LLM-jobb. 2M tokens ≈ ~20 kr med Gemini flash-prissättningen
    # (lib/admin/halsa.ts). 0 = grinden avstängd (test/dev utan databas har
    # inget att skydda). Sätts per miljö via LEADS_DAILY_TOKEN_BUDGET.
    leads_daily_token_budget: int = 2_000_000
    # Fas R2 (bd snipe-cku): semantisk svarscache. "off" (default): cachen
    # rörs aldrig — varken lookup eller store, inte ens ett embedding-anrop.
    # "shadow": lookup+store körs, men en TRÄFF ändrar inget i svaret, bara
    # en platform_events-rad för att mäta träffkvalitet innan man litar på
    # den. "on": en TRÄFF returneras till kunden och kostar noll LLM-anrop.
    # Se app/cache/svarscache.py och INV-CACHE-001. DEFAULT off i KOD med
    # flit — shadow/on slås på per miljö via env-variabeln SEMANTIC_CACHE,
    # aldrig som en kodändring. scripts/kor_evals.py sätter den explicit
    # till "off" — evals mäter modellen, inte cachen.
    semantic_cache: str = "off"
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
    # XOAUTH2 är förstahandsvalet för Gmail. Refresh-token ger nya kortlivade
    # access-tokens; inga access-tokens sparas i env eller databas.
    imap_oauth_client_id: str = ""
    imap_oauth_client_secret: str = ""
    imap_oauth_refresh_token: str = ""
    imap_oauth_token_url: str = "https://oauth2.googleapis.com/token"

    # Publik bas-URL för länkar som hamnar i utgående mejl (idag bara
    # avregistreringslänken). MÅSTE peka på Next-appen, inte på det här API:t —
    # det är Next som renderar /avregistrera/<token>.
    #
    # Tom => `app/leads/utskicksfot.py` kan inte bygga en fungerande länk, och
    # då blockerar send_guard regel 2 utskicket. Det är rätt utfall: ett
    # kallmejl med en trasig avregistreringslänk är värre än inget kallmejl.
    publik_bas_url: str = ""

    # SMTP-uppgifterna för snajpsupport@gmail.com. ETT konto för HELA
    # plattformen — det här är prioriterade mejl till OSS, inte kundutskick,
    # och har ingenting med per-tenant-avsändare att göra (se
    # app/notifications/prioriterat_mejl.py).
    #
    # Variabelnamnen behålls trots att modulen bytt namn: de sitter i Railway
    # och i DEPLOY.md, och att döpa om dem är en driftändring — inte en
    # omdöpning i koden.
    #
    # Lösenordet är INTE kontolösenordet. Ett Gmail med tvåstegsverifiering kan
    # inte logga in på SMTP med det; det kräver ett app-specifikt lösenord.
    # Sätts i Railway av en människa, samma sorts post som OPENAI_API_KEY i
    # docs/JURIDIK_ATGARDER.md.
    #
    # Ligger HÄR och inte i en `os.getenv` inne i modulen, och det är inte
    # kosmetika: pydantic-settings läser snajp-support/.env utan att exportera
    # något till os.environ, så en direktläsning hade sett värdena i Railway
    # men aldrig lokalt. Tomt => inga mejl skickas, och modulen loggar i stället.
    internlarm_smtp_anvandare: str = ""
    internlarm_smtp_losenord: str = ""

    # KUNDVÄND utgående SMTP — sändvägen för leads-utskick och godkända
    # supportsvar (app/leads/send_provider.py, app/email_pipeline/sender.py).
    # Skild från internlarmet ovan av samma skäl som prioriterat_mejl.py
    # skriver ut: de två vägarna får aldrig dela konto eller egenskaper.
    #
    # ETT konto för hela plattformen i v1 ("utskick från kundens egen domän"
    # är Del F och kräver per-tenant-credentials som inte är modellerade).
    # Alla tre första måste vara satta för att SmtpMailer ska väljas —
    # halvsatt räknas som osatt, precis som för internlarmet.
    #
    # Port 465 betyder implicit TLS (SMTP_SSL), allt annat STARTTLS.
    # Lösenordet är ett app-lösenord, inte kontolösenordet. Sätts i Railway
    # av en människa (CLAUDE.md-undantaget), aldrig i en fil som deployas.
    smtp_host: str = ""  # t.ex. smtp.gmail.com
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # Avsändaradress i From:. Tom => smtp_user. Visningsnamnet är valfritt.
    smtp_from: str = ""
    smtp_from_name: str = ""

    # Vilken KANAL utskicken går genom: "smtp" eller "resend".
    #
    # VARFÖR VALET FINNS: hostingplattformarna blockerar utgående SMTP på sina
    # billiga planer. Render gjorde det 2026-07-30 (commit 0d3ac1d, felet syntes
    # som "[Errno 101] Network is unreachable" först i det skarpa testet), och
    # Railway blockerar portarna 25/465/587/2525 på Free, Trial och Hobby —
    # bara Pro och uppåt släpper igenom. Projektet ligger på trial.
    #
    # Resend skickar över vanlig HTTPS och berörs därför inte alls. Det är inte
    # ett kringgående av en spärr: spärren finns för att skydda plattformens
    # IP-rykte mot skräppost, och en avsändare med verifierad domän och DKIM är
    # precis vad den vill se i stället.
    #
    # Tomt värde => härleds: finns RESEND_API_KEY väljs resend, annars smtp.
    # Att inte tvinga fram en explicit inställning gör att en satt nyckel
    # räcker för att sändvägen ska börja fungera.
    email_provider: str = ""
    resend_api_key: str = ""
    resend_webhook_secret: str = ""

    # Skatteverkets Beskattningsengagemang-API — verifierar tenantens EGET
    # orgnr vid onboarding (F-skatt, moms, arbetsgivarregistrering).
    # Tomma => app/leads/skatteverket.py returnerar ingen klient och
    # onboardingen fortsätter på enbart Luhn-kontrollen, precis som idag.
    #
    # NYCKLARNA FINNS INTE ÄNNU och kan inte skaffas härifrån: Skatteverket
    # delar ut dem efter ansökan via formulär (testnycklar mot sandboxen,
    # produktionsnycklar först efter tecknat avtal). Det är ett avtalsbeslut
    # av samma slag som DeepSeek-frågan, inte ett kodbeslut.
    #
    # Bas-URL:en pekar på TESTMILJÖN som default, med flit. En felaktigt
    # satt produktionsnyckel mot testmiljön svarar 401; en testnyckel mot
    # produktion hade slagit mot riktiga beskattningsuppgifter. Fel håll att
    # falla åt är det senare.
    skatteverket_client_id: str = ""
    skatteverket_client_secret: str = ""
    skatteverket_api_bas_url: str = "https://api.test.skatteverket.se"

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

        ## Varför den inte längre bara läser miljönamnet

        Den gjorde det fram till 2026-08-24, och motiveringen var att "Railway
        sätter ALLTID RAILWAY_ENVIRONMENT_NAME, så miljönamnet är aldrig okänt
        där". Det var sant och ändå fel, för det antog att Railway är den enda
        värden.

        Det är den inte. Två Render-tjänster från den gamla stacken låg kvar
        levande, deployade automatiskt vid varje push till `main` och
        `development`, och startade med `provider=deepseek` mot en riktig
        Postgres. På Render finns ingen RAILWAY_ENVIRONMENT_NAME, så
        miljönamnet var tomt, så spärren tolkade det som utveckling och släppte
        igenom. Den gren av villkoret som var tänkt att skydda en lokal körning
        skyddade i stället en bortglömd produktionsyta från att bli upptäckt.

        ## Regeln nu: databasen avgör, inte värdnamnet

        En riktig databas är det som gör data riktig. En process som kan öppna
        en REMOTE databas kan nå riktiga personuppgifter, oavsett vem som kör
        den och vad miljön råkar heta.

        Undantaget är en databas på loopback — `scripts/lokal_stack.py` kör mot
        127.0.0.1, och den stacken är tom och syntetisk. Det undantaget är
        smalt med flit: det gäller adressen, inte en flagga någon kan sätta.

        Tre utfall:

          * Känt miljönamn ur MILJOER_MED_KUNDDATA  -> riktig data
          * Databas som INTE är loopback            -> riktig data
          * Ingen databas, eller loopback           -> syntetisk

        Testsviten sätter tom DATABASE_URL (tests/conftest.py) och faller
        därför i tredje fallet, som förut.
        """
        if self.aktiv_miljo() in MILJOER_MED_KUNDDATA:
            return True
        return bool(self.database_url) and not _ar_loopback(self.database_url)

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

        modellens_provider = provider_for_model(self.model)
        if modellens_provider is not None and modellens_provider != self.llm_provider:
            return (
                f"MODEL={self.model!r} är en {modellens_provider}-modell, men "
                f"LLM_PROVIDER={self.llm_provider!r}. Anropet går till "
                f"{self.llm_provider}s endpoint med ett modellnamn som inte finns "
                f"där, och svaret blir 404 på VARJE förfrågan — medan "
                f"hälsokontrollen rapporterar 'live', eftersom en nyckel finns. "
                f"Sätt MODEL till en {self.llm_provider}-modell, eller ta bort "
                f"variabeln och låt koden välja default."
            )

        if self.llm_provider == "deepseek" and self.har_riktig_kunddata():
            # Skälet formuleras efter VAD som fällde, inte som en generisk
            # rad. Meddelandet är det enda någon läser när en deploy dör
            # 23:01, och "miljön ''" besvarar inte frågan varför.
            if self.aktiv_miljo() in MILJOER_MED_KUNDDATA:
                varfor = (
                    f"Miljön '{self.aktiv_miljo()}' bär eller speglar riktig kunddata."
                )
            else:
                varfor = (
                    f"Miljönamnet är okänt, men DATABASE_URL pekar på en databas "
                    f"som inte kör på den här maskinen ({_vard_ur_dsn(self.database_url)}). "
                    f"En process som kan öppna en fjärrdatabas kan nå riktiga "
                    f"personuppgifter, oavsett vilken värd den kör på — det var "
                    f"precis så den bortglömda Render-stacken kunde köra DeepSeek "
                    f"mot skarp data utan att någon spärr sa ifrån."
                )
            return (
                f"LLM_PROVIDER=deepseek är inte tillåtet här. {varfor} DeepSeek "
                f"behandlar prompten i Kina, och vi har varken SCC, "
                f"överföringsbedömning eller PUB-villkor på plats. "
                f"Sätt en tillåten provider (openai eller gemini) med rätt nyckel, "
                f"eller stäng av tjänsten om den inte ska köra alls."
            )
        return None

    def master_key_fault(self) -> str | None:
        """Varför masternyckeln inte duger här, eller None.

        Fältets default (`snajp_master_dev_key_change_me`) är incheckad i
        repot och accepteras rakt av i `deps.require_master_key` — och bakom
        just den nyckeln ligger HELA `/api/admin/*`, alltså cross-tenant-
        läsning av varje kunds data. En miljö som glömt sätta
        `SNAJP_MASTER_API_KEY` hade alltså stått med en publikt nåbar
        admin-yta vars lösenord står på GitHub.

        Samma gräns som `har_riktig_kunddata`: en process utan databas kan
        inte läcka kunddata och får behålla dev-defaulten (lokal körning,
        testsviten, MemoryStorage). En process MED databas vägrar starta —
        av samma skäl som dataskyddsspärren kraschar i stället för att varna.
        """
        if self.database_url and self.snajp_master_api_key == "snajp_master_dev_key_change_me":
            return (
                "SNAJP_MASTER_API_KEY är inte satt — masternyckeln står kvar på "
                "den incheckade dev-defaulten, och den låser upp hela "
                "/api/admin/* mot en databas med riktig kunddata. Sätt en egen "
                "nyckel i miljön (python scripts/keys.py) och deploya om."
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
