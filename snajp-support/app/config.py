"""Central konfiguration för Snajp-Support-tjänsten."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Default-tenanten (Nordlys Handel) — samma fasta UUID som i 003_snajp_multitenant.sql.
DEFAULT_TENANT_ID = "00000000-0000-4000-a000-000000000001"
DEFAULT_TENANT_SLUG = "nordlys-handel"
DEFAULT_TENANT_NAME = "Nordlys Handel"

CATEGORIES = (
    "teknisk_support",
    "leverans",
    "betalning",
    "retur_reklamation",
    "konto",
    "ovrigt",
)

CATEGORY_LABELS = {
    "teknisk_support": "Teknisk support",
    "leverans": "Leverans",
    "betalning": "Betalning",
    "retur_reklamation": "Retur & reklamation",
    "konto": "Konto",
    "ovrigt": "Övrigt",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    database_url: str = ""
    redis_url: str = ""
    snajp_master_api_key: str = "snajp_master_dev_key_change_me"
    snajp_demo_api_key: str = "snajp_demo_2f8c1a9e4b7d"

    def is_simulation(self) -> bool:
        # Samma platshållar-heuristik som app/api/email-studio/route.ts i Next-appen.
        key = self.openai_api_key or ""
        return len(key) < 20 or "..." in key or "din-" in key


@lru_cache
def get_settings() -> Settings:
    return Settings()
