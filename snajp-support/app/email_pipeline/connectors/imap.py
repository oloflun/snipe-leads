"""IMAP-connector — täcker både Gmail och Microsoft 365/Outlook.

- Gmail:   IMAP_HOST=imap.gmail.com, IMAP_USER=<adress>, IMAP_PASSWORD=<app-lösenord>
- Outlook: IMAP_HOST=outlook.office365.com, samma mönster.

Hämtar olästa mail, extraherar text + bildbilagor (som data-URLs) och markerar
dem lästa. imaplib är synkron — körs i trådpool så event-loopen aldrig blockeras.
Alla fel fångas och returneras som tom lista + felmeddelande; pipelinen kraschar
aldrig på en trasig inkorg eller utgången token.
"""

import asyncio
import base64
import email
import email.header
import email.utils
import imaplib
import logging

from ..models import InboundAttachment, InboundEmail

logger = logging.getLogger("snajp-support.imap")

MAX_ATTACHMENT_BYTES = 4_000_000
MAX_MESSAGES_PER_SYNC = 20


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for text, charset in email.header.decode_header(value):
        if isinstance(text, bytes):
            parts.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(text)
    return "".join(parts)


def _extract_body_text(message: email.message.Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        for part in message.walk():
            if part.get_content_type() == "text/html" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if payload:
                    import re

                    charset = part.get_content_charset() or "utf-8"
                    html = payload.decode(charset, errors="replace")
                    return re.sub(r"<[^>]+>", " ", html)
        return ""
    payload = message.get_payload(decode=True)
    if payload:
        charset = message.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    return ""


def _extract_attachments(message: email.message.Message) -> list[InboundAttachment]:
    attachments: list[InboundAttachment] = []
    if not message.is_multipart():
        return attachments
    for part in message.walk():
        filename = part.get_filename()
        if not filename:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        content_type = part.get_content_type()
        is_image = content_type.startswith("image/")
        data_url = None
        if len(payload) <= MAX_ATTACHMENT_BYTES:
            data_url = f"data:{content_type};base64,{base64.b64encode(payload).decode()}"
        attachments.append(
            InboundAttachment(
                filename=_decode_header(filename),
                content_type=content_type,
                data_url=data_url,
                is_image=is_image,
                size_bytes=len(payload),
            )
        )
    return attachments


def _fetch_sync(host: str, user: str, password: str, folder: str) -> list[InboundEmail]:
    emails: list[InboundEmail] = []
    client = imaplib.IMAP4_SSL(host, timeout=30)
    try:
        client.login(user, password)
        client.select(folder)
        _, data = client.search(None, "UNSEEN")
        message_ids = data[0].split()[:MAX_MESSAGES_PER_SYNC]
        for msg_id in message_ids:
            _, msg_data = client.fetch(msg_id, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            message = email.message_from_bytes(msg_data[0][1])
            from_name, from_email = email.utils.parseaddr(message.get("From", ""))
            received = None
            if message.get("Date"):
                try:
                    received = email.utils.parsedate_to_datetime(message["Date"]).isoformat()
                except Exception:
                    received = None
            emails.append(
                InboundEmail(
                    provider="imap",
                    provider_message_id=message.get("Message-ID") or f"imap-{msg_id.decode()}",
                    from_email=from_email or "okand@avsandare.se",
                    from_name=_decode_header(from_name) or None,
                    subject=_decode_header(message.get("Subject")),
                    body_text=_extract_body_text(message).strip()[:8000],
                    received_at=received,
                    attachments=_extract_attachments(message),
                )
            )
            client.store(msg_id, "+FLAGS", "\\Seen")
    finally:
        try:
            client.logout()
        except Exception:
            pass
    return emails


async def fetch_new(
    host: str, user: str, password: str, folder: str = "INBOX"
) -> tuple[list[InboundEmail], str | None]:
    """Returnerar (mail, felmeddelande). Kastar aldrig."""
    try:
        emails = await asyncio.to_thread(_fetch_sync, host, user, password, folder)
        return emails, None
    except imaplib.IMAP4.error as error:
        logger.warning("IMAP-autentisering/protokollfel: %s", error)
        return [], f"IMAP-fel (utgången token/fel lösenord?): {error}"
    except Exception as error:  # noqa: BLE001 — inkorgen får aldrig fälla tjänsten
        logger.warning("IMAP-hämtning misslyckades: %s", error)
        return [], f"IMAP-hämtning misslyckades: {error}"
