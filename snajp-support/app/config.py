"""Central konfiguration för Snajp-Support-tjänsten."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Demo-tenanten (Nordlys Handel) — samma fasta UUID som i 003_snajp_multitenant.sql.
# Publik: nås av marknadsföringsdemon och innehåller ENBART testmail.
DEFAULT_TENANT_ID = "00000000-0000-4000-a000-000000000001"
DEFAULT_TENANT_SLUG = "nordlys-handel"
DEFAULT_TENANT_NAME = "Nordlys Handel"

# Pilot-tenanten — skyddad arbetsyta med riktig kundinkorg. Skapas vid uppstart
# när SNAJP_PILOT_API_KEY är satt. Håll dess data borta från den publika demon.
PILOT_TENANT_ID = "00000000-0000-4000-a000-000000000002"
PILOT_TENANT_SLUG = "pilot"

CATEGORIES = (
    "teknisk_support",
    "leverans",
    "betalning",
    "retur_reklamation",
    "orderstatus",
    "konto",
    "ovrigt",
)

CATEGORY_LABELS = {
    "teknisk_support": "Teknisk support",
    "leverans": "Leverans",
    "betalning": "Betalning",
    "retur_reklamation": "Retur & reklamation",
    "orderstatus": "Orderstatus",
    "konto": "Konto",
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
    # Pilotens nyckel. Tom => ingen pilot-arbetsyta (bara publik demo).
    snajp_pilot_api_key: str = ""
    pilot_tenant_name: str = "Pilot"

    # Email-pipeline
    inbox_poll_seconds: int = 0  # 0 = ingen bakgrundspolling (mock triggas manuellt)
    auto_send_min_confidence: float = 0.75
    imap_host: str = ""  # t.ex. imap.gmail.com eller outlook.office365.com
    imap_user: str = ""
    imap_password: str = ""  # Gmail: app-lösenord; Outlook: app-lösenord/IMAP-auth
    imap_folder: str = "INBOX"
    # Vilken arbetsyta den riktiga inkorgen tillhör. "pilot" = bara pilot-tenanten
    # får synka; den publika demon blockeras och kan aldrig dra in riktiga mail.
    imap_tenant: str = "pilot"

    # Utgående mail. Tomma fält ärver IMAP-uppgifterna (samma Gmail-konto).
    smtp_host: str = ""  # tom + Gmail-IMAP => smtp.gmail.com
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Kundtjänst"

    # HÅRD SPÄRR: autosvar skickas aldrig utan att en människa godkänt, oavsett
    # vad kategorireglerna säger. Sätt till true först när piloten är utvärderad.
    allow_auto_send: bool = False

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

    def smtp_credentials(self) -> tuple[str, int, str, str]:
        """(host, port, user, password) — ärver IMAP-kontot när SMTP inte är satt."""
        user = self.smtp_user or self.imap_user
        password = self.smtp_password or self.imap_password
        host = self.smtp_host
        if not host and self.imap_host:
            # Gmail/Outlook har kända SMTP-motsvarigheter till sina IMAP-värdar.
            known = {
                "imap.gmail.com": "smtp.gmail.com",
                "outlook.office365.com": "smtp.office365.com",
            }
            host = known.get(self.imap_host.lower(), "")
        return host, self.smtp_port, user, password

    def can_send_email(self) -> bool:
        host, _, user, password = self.smtp_credentials()
        return bool(host and user and password)

    def imap_tenant_id(self) -> str:
        """Vilken tenant som äger den konfigurerade inkorgen."""
        return PILOT_TENANT_ID if self.imap_tenant == "pilot" else DEFAULT_TENANT_ID

    def is_simulation(self) -> bool:
        # Samma platshållar-heuristik som app/api/email-studio/route.ts i Next-appen.
        key = self.active_llm_key() or ""
        return len(key) < 20 or "..." in key or "din-" in key


@lru_cache
def get_settings() -> Settings:
    return Settings()
