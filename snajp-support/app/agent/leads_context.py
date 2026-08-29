"""Körningskontext för leads-agenterna (onboarding, outreach) — samma roll
som SupportContext, men för Fas A/C. Delar inte SupportContext eftersom
fälten är olika (ingen ticket/kategori, en offer/tråd i stället)."""

from dataclasses import dataclass, field
from typing import Any

from ..leads.skatteverket import SkatteverketAtkomst
from ..storage.base import Storage


@dataclass
class OnboardingContext:
    storage: Storage
    tenant_id: str
    saved_docs: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    #: Sätts av SERVERN efter BankID-inloggning mot Skatteverket, aldrig av
    #: modellen (INV-SEC-002). None = uppslaget är inte tillgängligt.
    skatteverket: SkatteverketAtkomst | None = None


@dataclass
class ResearchContext:
    """Fas B. Bär prospect_id så research_tools.scrape_registered_source
    kan kontrollera url-argumentet mot prospect_sources FÖR DET HÄR
    prospektet — inte mot alla prospekt i tenanten."""

    storage: Storage
    tenant_id: str
    prospect_id: str
    scraped_sources: list[dict[str, Any]] = field(default_factory=list)
    #: Sätts av SERVERN efter BankID-inloggning mot Skatteverket, aldrig av
    #: modellen (INV-SEC-002). None = uppslaget är inte tillgängligt.
    skatteverket: SkatteverketAtkomst | None = None


@dataclass
class OutreachContext:
    storage: Storage
    tenant_id: str
    thread_id: str
    prospect_email: str
    #: Var i sekvensen det här meddelandet ligger. 0 = första kontakten.
    #: Avgör tillsammans med autonominivån om utkastet får skickas eller
    #: måste granskas (app/leads/autonomy.py).
    sequence_index: int = 0
    queued: bool = False
    escalated: bool = False
    escalation_reason: str | None = None
    #: Sätts av SERVERN efter BankID-inloggning mot Skatteverket, aldrig av
    #: modellen (INV-SEC-002). None = uppslaget är inte tillgängligt.
    #:
    #: OBS: gäller TENANTENS eget bolag, aldrig prospektets — trots att den
    #: här kontexten annars handlar om prospektet. Tokenen är utfärdad för den
    #: inloggade kunden och Skatteverket svarar 403 på någon annans identitet;
    #: villkorens §7.1 förbjuder dessutom uppslag på tredje part.
    skatteverket: SkatteverketAtkomst | None = None
