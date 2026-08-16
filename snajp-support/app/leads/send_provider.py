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
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

logger = logging.getLogger("snajp-support.send-provider")


class SendProvider(Protocol):
    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class LoggingSendProvider:
    """Default. Skickar inget riktigt mail — loggar och returnerar. Ersätts
    av en SMTP-provider när en tenants SMTP-credentials finns konfigurerade."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("SIMULERAT UTSKICK till %s: %r (%d tecken)", to, subject, len(body))


class DryRunMailer:
    """Skriver HELA mejlet till en fil i stället för att skicka det.

    Skillnaden mot `LoggingSendProvider` är att den här bevarar brödtexten.
    Loggraden säger att ett utskick skedde; filen säger VAD som stod i det —
    och det är det senare som går att granska. En sidfot som tappat
    organisationsnumret syns inte i "SIMULERAT UTSKICK till x (412 tecken)".

    Det här är default vid all lokal verifiering. Riktig SMTP kopplas in först
    när en människa uttryckligen sagt till, och `get_send_provider` returnerar
    aldrig något som når internet utan att en miljövariabel satts.
    """

    def __init__(self, outbox: str | Path) -> None:
        self.outbox = Path(outbox)

    async def send(self, *, to: str, subject: str, body: str) -> None:
        self.outbox.mkdir(parents=True, exist_ok=True)
        nu = datetime.now(timezone.utc)
        filnamn = f"{nu:%Y%m%dT%H%M%S%f}-{_filnamnssaker(to)}.eml"
        sokvag = self.outbox / filnamn

        # Headers + body, i den form ett riktigt mejl har. Att skriva bara
        # brödtexten hade gjort filen oanvändbar för att granska adressering
        # och ämnesrad, vilket är två av de tre sakerna som går fel.
        sokvag.write_text(
            "\n".join(
                [
                    f"Date: {nu:%a, %d %b %Y %H:%M:%S +0000}",
                    f"To: {to}",
                    f"Subject: {subject}",
                    "X-Snajp-Provider: DryRunMailer (INGET SKICKAT)",
                    "",
                    body,
                ]
            ),
            encoding="utf-8",
        )
        logger.info("TORRKÖRNING: mejlet till %s skrevs till %s", to, sokvag)


def _filnamnssaker(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", text)[:80] or "okand"


def get_send_provider() -> SendProvider:
    """Väljer provider. Ingen av vägarna når internet.

    `SNAJP_OUTBOX_DIR` slår på torrkörningen. Den sätts i `.env.local` och
    ALDRIG i något som deployas — se DEL 2.2. Att den är opt-in och inte
    default betyder att produktionen beter sig exakt som förut tills någon
    aktivt ändrar det.

    En riktig SMTP-provider finns fortfarande inte. Det är avsiktligt: att
    slå på utskick är att skriva den klassen, inte att sätta en flagga.
    """
    outbox = os.environ.get("SNAJP_OUTBOX_DIR", "").strip()
    if outbox:
        return DryRunMailer(outbox)
    return LoggingSendProvider()
