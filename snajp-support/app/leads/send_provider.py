"""Den faktiska sändvägen — den ENDA plats i kodbasen som får sätta ett
send_queue-item till 'sent' (INV-SEC-004: modellen kan bara köa).

Tre providers, i fallande allvar:

  * `SmtpMailer` — riktig sändning, väljs BARA när SMTP_HOST + SMTP_USER +
    SMTP_PASSWORD alla är satta. ETT konto för hela plattformen i v1;
    per-tenant-avsändare ("utskick från kundens egen domän", Del F) kräver
    credentials som inte är modellerade än — samma lucka som fanns för IMAP
    innan IMAP_PASSWORD_<SLUG> etablerades (TENANTS.md).
  * `DryRunMailer` — skriver mejlet till fil. Vinner ÖVER SmtpMailer om båda
    råkar vara konfigurerade: den som satt SNAJP_OUTBOX_DIR håller på att
    verifiera något lokalt, och det värsta utfallet av den kollisionen ska
    vara en .eml-fil för mycket, aldrig ett riktigt mejl för mycket.
  * `LoggingSendProvider` — default. Loggar avsikten, skickar inget, och
    tjänsten degraderar gracefully utan konfiguration (samma mönster som
    MemoryStorage/simuleringsläge).

`levererar`-attributet är kontraktet mot anroparna: bara en provider med
`levererar = True` når internet, och det är det attributet — inte typen —
som t.ex. supportens godkännandeväg läser för att veta om "skickat" är sant.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Protocol

from ..config import Settings, get_settings

logger = logging.getLogger("snajp-support.send-provider")

#: Tak för en hel SMTP-session. Skickningen körs i schemaläggarloopen och i
#: godkännande-requests; en server som inte svarat på tjugo sekunder kommer
#: inte att svara på trettio, och anroparen ska få veta det medan den
#: fortfarande kan agera på det.
SMTP_TIDSTAK_SEKUNDER = 20.0


class SendProvider(Protocol):
    #: True bara för providers som faktiskt når internet.
    levererar: bool

    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class LoggingSendProvider:
    """Default. Skickar inget riktigt mail — loggar och returnerar."""

    levererar = False

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("SIMULERAT UTSKICK till %s: %r (%d tecken)", to, subject, len(body))


class SmtpMailer:
    """Riktig sändning över SMTP. Kastar vid fel — med flit.

    Anroparna markerar 'sent' EFTER ett lyckat anrop, och ett undantag härifrån
    är vad som håller den ordningen ärlig: ett mejl som inte gick fram får
    aldrig bli en 'sent'-rad. Schemaläggaren fångar per post (process_all_due)
    så posten blir kvar som 'queued' och prövas igen; godkännandevägen
    översätter till 502 så människan ser att inget skickades.

    Samma trådmönster som prioriterat_mejl.py och av samma skäl: smtplib är
    blockerande, och rakt på event-loopen stannar hela tjänsten så länge
    SMTP-servern funderar.
    """

    levererar = True

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        avsandare: str,
        avsandarnamn: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.avsandare = avsandare
        self.avsandarnamn = avsandarnamn

    def _blockerande(self, *, to: str, subject: str, body: str) -> None:
        meddelande = EmailMessage()
        meddelande["Subject"] = subject
        meddelande["From"] = (
            formataddr((self.avsandarnamn, self.avsandare)) if self.avsandarnamn else self.avsandare
        )
        meddelande["To"] = to
        meddelande.set_content(body)

        # 465 är implicit TLS från första byte (SMTPS); allt annat är klartext
        # som uppgraderas med STARTTLS. Att alltid köra starttls() mot 465
        # hänger sig i stället för att fela — servern väntar på TLS-handskakning
        # medan klienten väntar på ett SMTP-hälsningsmeddelande.
        if self.port == 465:
            server_klass, behov_starttls = smtplib.SMTP_SSL, False
        else:
            server_klass, behov_starttls = smtplib.SMTP, True

        with server_klass(self.host, self.port, timeout=SMTP_TIDSTAK_SEKUNDER) as server:
            if behov_starttls:
                server.starttls()
            server.login(self.user, self.password)
            server.send_message(meddelande)

    async def send(self, *, to: str, subject: str, body: str) -> None:
        adress = (to or "").strip()
        if not adress or "@" not in adress:
            # Hellre ett tydligt fel än ett SMTP-avvisande tre lager ned:
            # scheduler.py skickar "okänd" som fallback-adress när tråden
            # saknar prospect_email, och det värdet ska stoppas HÄR — synligt
            # — inte bli ett kryptiskt 501 från servern.
            raise ValueError(f"Ogiltig mottagaradress: {to!r} — inget skickat.")
        await asyncio.wait_for(
            asyncio.to_thread(self._blockerande, to=adress, subject=subject, body=body),
            timeout=SMTP_TIDSTAK_SEKUNDER + 5,
        )
        logger.info("SMTP-UTSKICK till %s: %r (%d tecken)", adress, subject, len(body))


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

    levererar = False

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


def get_send_provider(settings: Settings | None = None) -> SendProvider:
    """Väljer provider. Ordningen är en säkerhetsordning, inte en smaksak.

    1. `SNAJP_OUTBOX_DIR` (torrkörning) vinner över ALLT, även en komplett
       SMTP-konfiguration. Den sätts i `.env.local` för lokal verifiering, och
       om båda råkar vara satta ska felet vara en .eml-fil för mycket — aldrig
       ett riktigt mejl för mycket. Kollisionen loggas så den syns.
    2. Komplett SMTP-konfiguration (host + user + password) ger `SmtpMailer` —
       den enda vägen till internet, opt-in via tre variabler som bara en
       människa sätter i Railway.
    3. Allt annat ger `LoggingSendProvider`, som skickar ingenting. En HALVSATT
       SMTP-konfiguration hamnar också här, med en varning: den som satt en av
       tre variabler tror sig ha en sändväg och har det inte, och /health-radens
       "Ingen riktig sändväg" är då ledtråden.

    `settings`-parametern finns för testerna; anropsplatserna i drift skickar
    inget och får den cachade konfigurationen.
    """
    settings = settings or get_settings()

    outbox = os.environ.get("SNAJP_OUTBOX_DIR", "").strip()
    if outbox:
        if settings.smtp_host:
            logger.warning(
                "SNAJP_OUTBOX_DIR och SMTP_HOST är BÅDA satta — torrkörningen "
                "vinner och ingenting skickas. Ta bort SNAJP_OUTBOX_DIR när "
                "riktig sändning är avsikten."
            )
        return DryRunMailer(outbox)

    host = (settings.smtp_host or "").strip()
    user = (settings.smtp_user or "").strip()
    losenord = (settings.smtp_password or "").strip()
    if host and user and losenord:
        return SmtpMailer(
            host=host,
            port=settings.smtp_port,
            user=user,
            password=losenord,
            avsandare=(settings.smtp_from or "").strip() or user,
            avsandarnamn=(settings.smtp_from_name or "").strip(),
        )
    if host or user or losenord:
        logger.warning(
            "SMTP-konfigurationen är halvsatt (host=%s, user=%s, lösenord=%s) — "
            "faller tillbaka på LoggingSendProvider, ingenting skickas.",
            "satt" if host else "saknas",
            "satt" if user else "saknas",
            "satt" if losenord else "saknas",
        )
    return LoggingSendProvider()
