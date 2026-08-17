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

    # LLM-provider: "openai" eller "deepseek" (OpenAI-kompatibel endpoint).
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
        # Undvik footgun: gpt-default mot DeepSeek => byt till deepseek-v4-flash
        # (1M kontext, 384K output, $0.14/$0.28 per 1M token — se plan-dokumentet).
        if self.llm_provider == "deepseek" and self.model.startswith("gpt-"):
            self.model = "deepseek-v4-flash"
        return self

    def active_llm_key(self) -> str:
        if self.llm_provider == "deepseek":
            return self.deepseek_api_key
        return self.openai_api_key

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
