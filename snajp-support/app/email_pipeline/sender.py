"""Utgående mail via SMTP (Gmail eller valfri server).

Svaret skickas som ett svar i samma mailtråd som kundens ursprungliga mail:
`In-Reply-To` och `References` sätts från originalets Message-ID, och ämnet
prefixas med "Re:". Utan det hamnar svaret som en lös tråd i kundens inkorg.

smtplib är synkron — körs i trådpool så event-loopen aldrig blockeras.
Alla fel fångas och returneras som (False, felmeddelande); anroparen avgör
vad som ska hända. Ett ärende får ALDRIG markeras som skickat om detta
misslyckas — då väntar kunden på ett svar som aldrig kom.
"""

import asyncio
import logging
import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from ..config import get_settings

logger = logging.getLogger("snajp-support.sender")


def _normalise_message_id(raw: str | None) -> str | None:
    """Message-ID måste ha vinkelparenteser för att trådning ska fungera."""
    if not raw:
        return None
    value = raw.strip()
    if not value or not re.match(r"^<?[^<>@\s]+@[^<>@\s]+>?$", value):
        return None  # mock-/API-id:n är inte riktiga Message-ID:n
    return value if value.startswith("<") else f"<{value}>"


def _send_sync(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    from_name: str,
    to_email: str,
    subject: str,
    body: str,
    in_reply_to: str | None,
) -> str:
    message = EmailMessage()
    message["From"] = formataddr((from_name, user))
    message["To"] = to_email
    message["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    message["Message-ID"] = make_msgid()
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(message)
    return message["Message-ID"]


async def send_reply(
    *,
    to_email: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
) -> tuple[bool, str]:
    """Skickar ett svar. Returnerar (lyckades, meddelande-id eller felbeskrivning)."""
    settings = get_settings()
    host, port, user, password = settings.smtp_credentials()

    if not (host and user and password):
        return False, (
            "SMTP är inte konfigurerat (SMTP_HOST/SMTP_USER/SMTP_PASSWORD, eller "
            "IMAP-uppgifterna som fallback). Svaret har inte skickats."
        )

    try:
        message_id = await asyncio.to_thread(
            _send_sync,
            host=host,
            port=port,
            user=user,
            password=password,
            from_name=settings.smtp_from_name,
            to_email=to_email,
            subject=subject,
            body=body,
            in_reply_to=_normalise_message_id(in_reply_to),
        )
        logger.info("Svar skickat till %s (%s)", to_email, message_id)
        return True, message_id
    except smtplib.SMTPAuthenticationError:
        logger.warning("SMTP-inloggning nekad för %s", user)
        return False, "SMTP-inloggningen nekades — kontrollera app-lösenordet."
    except smtplib.SMTPRecipientsRefused:
        return False, f"Mottagaradressen {to_email} avvisades av servern."
    except Exception as error:  # noqa: BLE001 — sändfel får aldrig fälla tjänsten
        logger.warning("SMTP-sändning misslyckades: %s", error)
        return False, f"Sändningen misslyckades: {error}"
