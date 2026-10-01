r"""IMAP-connector — täcker både Gmail och Microsoft 365/Outlook.

- Gmail:   IMAP_HOST=imap.gmail.com, IMAP_USER=<adress>, IMAP_PASSWORD=<app-lösenord>
- Outlook: IMAP_HOST=outlook.office365.com, samma mönster.

Hämtar olästa mail med BODY.PEEK (utan att röra \Seen) och extraherar text +
bildbilagor (som data-URLs). Läst-markeringen görs av anroparen via mark_seen()
EFTER lyckad ingest — ett mejl som markerats läst före databasskrivningen är
ett mejl som försvinner om skrivningen faller. imaplib är synkron — körs i
trådpool så event-loopen aldrig blockeras.
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
import re
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage

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


def _refresh_access_token(client_id: str, client_secret: str, refresh_token: str, token_url: str) -> str:
    """Hämta en kortlivad access-token utan att logga hemligheter."""
    data = urllib.parse.urlencode({
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token, "grant_type": "refresh_token",
    }).encode()
    request = urllib.request.Request(token_url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        import json
        payload = json.loads(response.read().decode())
    token = str(payload.get("access_token") or "")
    if not token:
        raise RuntimeError("OAuth-leverantören returnerade ingen access_token.")
    return token


def _xoauth2_bytes(user: str, access_token: str) -> bytes:
    return f"user={user}\x01auth=Bearer {access_token}\x01\x01".encode()


def _logga_in(client: imaplib.IMAP4_SSL, user: str, password: str, *,
              oauth_client_id: str = "", oauth_client_secret: str = "",
              oauth_refresh_token: str = "",
              oauth_token_url: str = "https://oauth2.googleapis.com/token") -> None:
    if oauth_client_id and oauth_client_secret and oauth_refresh_token:
        access_token = _refresh_access_token(
            oauth_client_id, oauth_client_secret, oauth_refresh_token, oauth_token_url
        )
        client.authenticate("XOAUTH2", lambda _: _xoauth2_bytes(user, access_token))
    else:
        client.login(user, password)


def _fetch_sync(
    host: str, user: str, password: str, folder: str, *,
    oauth_client_id: str = "", oauth_client_secret: str = "",
    oauth_refresh_token: str = "",
    oauth_token_url: str = "https://oauth2.googleapis.com/token",
) -> list[InboundEmail]:
    # UID + BODY.PEEK[], inte sekvensnummer + RFC822, och ingen \Seen-flagga
    # här. Den gamla vägen markerade mejlet läst INNAN ingest — föll databasen
    # efter hämtningen var mejlet borta för alltid (UNSEEN-sökningen ser det
    # aldrig igen). PEEK rör ingenting; pollern markerar via mark_seen() när
    # raden faktiskt står i databasen. UID och inte sekvensnummer för att
    # markeringen sker i en EGEN anslutning — sekvensnummer kan glida mellan
    # två select, UID:n står stilla så länge UIDVALIDITY gör det.
    emails: list[InboundEmail] = []
    client = imaplib.IMAP4_SSL(host, timeout=30)
    try:
        _logga_in(
            client, user, password,
            oauth_client_id=oauth_client_id, oauth_client_secret=oauth_client_secret,
            oauth_refresh_token=oauth_refresh_token, oauth_token_url=oauth_token_url,
        )
        client.select(folder)
        _, data = client.uid("search", None, "UNSEEN")
        message_uids = data[0].split()[:MAX_MESSAGES_PER_SYNC]
        for msg_uid in message_uids:
            _, msg_data = client.uid("fetch", msg_uid, "(BODY.PEEK[])")
            if not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple):
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
                    provider_message_id=message.get("Message-ID") or f"imap-{msg_uid.decode()}",
                    from_email=from_email or "okand@avsandare.se",
                    from_name=_decode_header(from_name) or None,
                    subject=_decode_header(message.get("Subject")),
                    body_text=_extract_body_text(message).strip()[:8000],
                    received_at=received,
                    attachments=_extract_attachments(message),
                    imap_uid=msg_uid.decode(),
                )
            )
    finally:
        try:
            client.logout()
        except Exception:
            pass
    return emails


def _mark_seen_sync(
    host: str, user: str, password: str, folder: str, uids: list[str], *,
    oauth_client_id: str = "", oauth_client_secret: str = "",
    oauth_refresh_token: str = "",
    oauth_token_url: str = "https://oauth2.googleapis.com/token",
) -> None:
    client = imaplib.IMAP4_SSL(host, timeout=30)
    try:
        _logga_in(
            client, user, password,
            oauth_client_id=oauth_client_id, oauth_client_secret=oauth_client_secret,
            oauth_refresh_token=oauth_refresh_token, oauth_token_url=oauth_token_url,
        )
        client.select(folder)
        client.uid("store", ",".join(uids), "+FLAGS", "\\Seen")
    finally:
        try:
            client.logout()
        except Exception:
            pass


def _prova_sync(host: str, user: str, password: str) -> None:
    client = imaplib.IMAP4_SSL(host, timeout=15)
    try:
        client.login(user, password)
    finally:
        try:
            client.logout()
        except Exception:
            pass


async def prova_inloggning(host: str, user: str, password: str) -> str | None:
    """Provar en IMAP-inloggning. None när den lyckas, annars ett KUNDVÄNLIGT fel.

    Körs när kunden kopplar sin inkorg: ett fel app-lösenord ska fångas i det
    ögonblicket, med ett besked som går att agera på — inte vid första synken
    som ett kryptiskt IMAP-fel på en inställningssida kunden redan lämnat.
    """
    try:
        await asyncio.to_thread(_prova_sync, host, user, password)
        return None
    except imaplib.IMAP4.error as error:
        logger.info("IMAP-inloggning nekades för %s@%s: %s", user, host, error)
        return (
            "Inloggningen nekades. Kontrollera att adressen stämmer och att du "
            "använder ett APP-LÖSENORD (inte ditt vanliga lösenord) — Gmail och "
            "iCloud kräver det, och Outlook kräver att IMAP är påslaget."
        )
    except Exception as error:  # noqa: BLE001 — nätfel ska ge besked, inte 500
        logger.warning("IMAP-inloggning mot %s gick inte att prova: %s", host, error)
        return f"Gick inte att nå mejlservern {host}. Försök igen om en stund."


async def mark_seen(
    host: str, user: str, password: str = "", folder: str = "INBOX",
    uids: list[str] | None = None, *,
    oauth_client_id: str = "", oauth_client_secret: str = "",
    oauth_refresh_token: str = "",
    oauth_token_url: str = "https://oauth2.googleapis.com/token",
) -> str | None:
    """Markerar UID:n som lästa EFTER lyckad ingest. None vid framgång,
    annars ett felmeddelande. Kastar aldrig — misslyckas markeringen hämtas
    mejlen igen nästa synk och faller bort som dubletter i ingest_email,
    vilket är den billiga sidan av felet (den dyra är ett tappat mejl)."""
    if not uids:
        return None
    try:
        await asyncio.to_thread(
            _mark_seen_sync, host, user, password, folder, uids,
            oauth_client_id=oauth_client_id,
            oauth_client_secret=oauth_client_secret,
            oauth_refresh_token=oauth_refresh_token,
            oauth_token_url=oauth_token_url,
        )
        return None
    except Exception as error:  # noqa: BLE001 — markeringen får aldrig fälla synken
        logger.warning("Kunde inte markera %d mejl som lästa: %s", len(uids), error)
        return f"Kunde inte markera mejlen som lästa: {error}"


async def fetch_new(
    host: str, user: str, password: str = "", folder: str = "INBOX", *,
    oauth_client_id: str = "", oauth_client_secret: str = "",
    oauth_refresh_token: str = "",
    oauth_token_url: str = "https://oauth2.googleapis.com/token",
) -> tuple[list[InboundEmail], str | None]:
    """Returnerar (mail, felmeddelande). Kastar aldrig."""
    try:
        emails = await asyncio.to_thread(
            _fetch_sync, host, user, password, folder,
            oauth_client_id=oauth_client_id,
            oauth_client_secret=oauth_client_secret,
            oauth_refresh_token=oauth_refresh_token,
            oauth_token_url=oauth_token_url,
        )
        return emails, None
    except imaplib.IMAP4.error as error:
        logger.warning("IMAP-autentisering/protokollfel: %s", error)
        return [], f"IMAP-fel (utgången token/fel lösenord?): {error}"
    except Exception as error:  # noqa: BLE001 — inkorgen får aldrig fälla tjänsten
        logger.warning("IMAP-hämtning misslyckades: %s", error)
        return [], f"IMAP-hämtning misslyckades: {error}"


#: Mappar att prova när LIST-svaret inte bär \Sent-attributet. Engelsk Gmail
#: först (vanligast), sedan de generiska namn Outlook/iCloud/cPanel använder.
SKICKAT_KANDIDATER = (
    "[Gmail]/Sent Mail",
    "Sent",
    "Sent Items",
    "Sent Messages",
    "INBOX.Sent",
)

#: En LIST-rad: (attribut) "avgränsare" mappnamn — namnet citerat eller inte.
_LIST_RAD = re.compile(rb'^\((?P<attrs>[^)]*)\)\s+(?:"(?:[^"]*)"|NIL)\s+(?P<namn>.+)$')


def _skickatmapp(client) -> str | None:
    """Mappen med \\Sent-attributet ur LIST (RFC 6154).

    Gmail och Outlook bär attributet i sitt vanliga LIST-svar, och det är
    enda pålitliga vägen: NAMNET är lokaliserat efter kontots språk — svensk
    Gmail heter "[Gmail]/Skickat", engelsk "[Gmail]/Sent Mail". Hårdkodade
    namn är bara fallback (SKICKAT_KANDIDATER)."""
    typ, rader = client.list()
    if typ != "OK":
        return None
    for rad in rader or []:
        if not isinstance(rad, bytes):
            continue
        traff = _LIST_RAD.match(rad.strip())
        if not traff or b"\\sent" not in traff.group("attrs").lower():
            continue
        namn = traff.group("namn").strip()
        if namn.startswith(b'"') and namn.endswith(b'"'):
            namn = namn[1:-1]
        # Modified UTF-7 (RFC 2060) är ren ASCII — namnet skickas tillbaka
        # till servern i exakt den form LIST gav det.
        return namn.decode("ascii", errors="replace")
    return None


def _spara_skickat_sync(
    host: str, user: str, password: str, *, fran: str, till: str, amne: str, brodtext: str
) -> None:
    client = imaplib.IMAP4_SSL(host, timeout=30)
    try:
        client.login(user, password)
        meddelande = EmailMessage()
        meddelande["From"] = fran or user
        meddelande["To"] = till
        meddelande["Subject"] = amne
        meddelande["Date"] = email.utils.formatdate()
        meddelande.set_content(brodtext)

        mappar = [m for m in (_skickatmapp(client),) if m] or list(SKICKAT_KANDIDATER)
        sista_fel: object = None
        for mapp in mappar:
            try:
                typ, svar = client.append(
                    f'"{mapp}"', "\\Seen", imaplib.Time2Internaldate(time.time()),
                    meddelande.as_bytes(),
                )
            except imaplib.IMAP4.error as error:
                sista_fel = error
                continue
            if typ == "OK":
                return
            sista_fel = svar
        raise RuntimeError(f"APPEND nekades av {host}: {sista_fel!r}")
    finally:
        try:
            client.logout()
        except Exception:
            pass


async def spara_i_skickat(
    host: str, user: str, password: str, *, fran: str, till: str, amne: str, brodtext: str
) -> str | None:
    """Lägger en kopia av ett skickat mejl i kontots Skickat-mapp (APPEND).

    Utskicken går över Resend/SMTP och passerar aldrig kundens eget konto —
    utan den här kopian är "Skickat" i kundens mejlklient tomt. None vid
    framgång, annars ett felmeddelande. Kastar aldrig: kopian är en
    bekvämlighet och får inte fälla eller fördröja sändningen den speglar.
    """
    try:
        await asyncio.to_thread(
            _spara_skickat_sync, host, user, password,
            fran=fran, till=till, amne=amne, brodtext=brodtext,
        )
        return None
    except Exception as error:  # noqa: BLE001 — kopian får aldrig fälla sändningen
        logger.warning("Kunde inte spara kopia i Skickat för %s@%s: %s", user, host, error)
        return f"Kopian till Skickat misslyckades: {error}"
