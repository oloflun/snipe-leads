"""Körningskontext för leads-agenterna (onboarding, outreach) — samma roll
som SupportContext, men för Fas A/C. Delar inte SupportContext eftersom
fälten är olika (ingen ticket/kategori, en offer/tråd i stället)."""

from dataclasses import dataclass, field
from typing import Any

from ..storage.base import Storage


@dataclass
class OnboardingContext:
    storage: Storage
    tenant_id: str
    saved_docs: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False


@dataclass
class ResearchContext:
    """Fas B. Bär prospect_id så research_tools.scrape_registered_source
    kan kontrollera url-argumentet mot prospect_sources FÖR DET HÄR
    prospektet — inte mot alla prospekt i tenanten."""

    storage: Storage
    tenant_id: str
    prospect_id: str
    scraped_sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class OutreachContext:
    storage: Storage
    tenant_id: str
    thread_id: str
    prospect_email: str
    queued: bool = False
    escalated: bool = False
    escalation_reason: str | None = None
