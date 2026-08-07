"""Den faktiska sändvägen — den ENDA plats i kodbasen som får sätta ett
send_queue-item till 'sent' (INV-SEC-004: modellen kan bara köa).

Riktig SMTP-integration (tenantens egen domän, Del F: "utskick från
kundens egen domän") kräver per-tenant SMTP-credentials som inte finns
modellerade än — samma lucka som fanns för IMAP innan
IMAP_PASSWORD_<SLUG> etablerades (TENANTS.md). LoggingSendProvider är
default tills dess: den skickar ingenting, loggar avsikten, och tjänsten
degraderar gracefully utan konfiguration (samma mönster som
MemoryStorage/simuleringsläge)."""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("snajp-support.send-provider")


class SendProvider(Protocol):
    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class LoggingSendProvider:
    """Default. Skickar inget riktigt mail — loggar och returnerar. Ersätts
    av en SMTP-provider när en tenants SMTP-credentials finns konfigurerade."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("SIMULERAT UTSKICK till %s: %r (%d tecken)", to, subject, len(body))


def get_send_provider() -> SendProvider:
    return LoggingSendProvider()
