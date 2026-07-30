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


async def _send_via_resend(
    *, to_email: str, subject: str, body: str, in_reply_to: str | None
) -> tuple[bool, str]:
    """Skickar över HTTPS i stället för SMTP.

    Krävs på Renders gratisplan, som blockerar utgående SMTP-portar sedan
    september 2025. Fungerar även där SMTP är öppet.
    """
    import httpx

    settings = get_settings()
    payload: dict[str, object] = {
        "from": f"{settings.smtp_from_name} <{settings.sender_address()}>",
        "to": [to_email],
        "subject": subject if subject.lower().startswith("re:") else f"Re: {subject}",
        "text": body,
    }
    reply_to = _normalise_message_id(in_reply_to)
    if reply_to:
        # Trådning: samma headers som SMTP-vägen sätter.
        payload["headers"] = {"In-Reply-To": reply_to, "References": reply_to}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
            )
        if response.status_code >= 400:
            return False, f"Resend avvisade sändningen ({response.status_code}): {response.text[:200]}"
        return True, response.json().get("id", "skickat")
    except Exception as error:  # noqa: BLE001 — sändfel får aldrig fälla tjänsten
        logger.warning("Resend-sändning misslyckades: %s", error)
        return False, f"Sändningen misslyckades: {error}"


async def send_reply(
    *,
    to_email: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
) -> tuple[bool, str]:
    """Skickar ett svar. Returnerar (lyckades, meddelande-id eller felbeskrivning)."""
    settings = get_settings()

    if settings.email_provider == "resend":
        if not settings.resend_api_key:
            return False, "RESEND_API_KEY saknas. Svaret har inte skickats."
        return await _send_via_resend(
            to_email=to_email, subject=subject, body=body, in_reply_to=in_reply_to
        )

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
    except OSError as error:
        # Renders gratisplan blockerar portarna 25/465/587 sedan sep 2025.
        if getattr(error, "errno", None) in (101, 111, 110):
            return False, (
                "Utgående SMTP är blockerat i den här miljön (vanligt på gratis "
                "hostingplaner). Sätt EMAIL_PROVIDER=resend med en RESEND_API_KEY, "
                "eller uppgradera till en betald plan."
            )
        return False, f"Sändningen misslyckades: {error}"
    except Exception as error:  # noqa: BLE001 — sändfel får aldrig fälla tjänsten
        logger.warning("SMTP-sändning misslyckades: %s", error)
        return False, f"Sändningen misslyckades: {error}"
