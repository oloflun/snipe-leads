"""Central konfiguration för Snajp-Support-tjänsten."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default-tenanten (Nordlys Handel) — samma fasta UUID som i 003_snajp_multitenant.sql.
DEFAULT_TENANT_ID = "00000000-0000-4000-a000-000000000001"
DEFAULT_TENANT_SLUG = "nordlys-handel"
DEFAULT_TENANT_NAME = "Nordlys Handel"

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
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM-provider: "openai" eller "deepseek" (OpenAI-kompatibel endpoint).
    llm_provider: str = "openai"
    llm_base_url: str = ""  # tom => härleds från provider (se agent/llm.py)
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    embedding_api_key: str = ""  # valfri OpenAI-nyckel — DeepSeek saknar embeddings
    model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    database_url: str = ""
    redis_url: str = ""
    snajp_master_api_key: str = "snajp_master_dev_key_change_me"
    snajp_demo_api_key: str = "snajp_demo_2f8c1a9e4b7d"

    # Email-pipeline
    inbox_poll_seconds: int = 0  # 0 = ingen bakgrundspolling (mock triggas manuellt)
    auto_send_min_confidence: float = 0.75
    imap_host: str = ""  # t.ex. imap.gmail.com eller outlook.office365.com
    imap_user: str = ""
    imap_password: str = ""  # Gmail: app-lösenord; Outlook: app-lösenord/IMAP-auth
    imap_folder: str = "INBOX"

    @model_validator(mode="after")
    def _default_model_for_provider(self) -> "Settings":
        # Undvik footgun: gpt-default mot DeepSeek => byt till deepseek-chat.
        if self.llm_provider == "deepseek" and self.model.startswith("gpt-"):
            self.model = "deepseek-chat"
        return self

    def active_llm_key(self) -> str:
        if self.llm_provider == "deepseek":
            return self.deepseek_api_key
        return self.openai_api_key

    def is_simulation(self) -> bool:
        # Samma platshållar-heuristik som app/api/email-studio/route.ts i Next-appen.
        key = self.active_llm_key() or ""
        return len(key) < 20 or "..." in key or "din-" in key


@lru_cache
def get_settings() -> Settings:
    return Settings()
