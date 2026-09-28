"""Bakgrundspolling av anslutna inkorgar.

Startas i lifespan om INBOX_POLL_SECONDS > 0.
Robust: varje varv fångar alla fel (utgången token, nätverk, OpenAI-timeout)
och loggar dem — tjänsten kraschar aldrig på en trasig inkorg.

Varje tenant har sin egen inkorg i ss_mailboxes. Lösenordet hämtas ur env med
tenantens slug som nyckel (IMAP_PASSWORD_<SLUG>) och lagras aldrig i databasen:
en läsbehörighet på ss_mailboxes ska inte räcka för att läsa kundens mail.
"""

import asyncio
import logging
import os

from ..config import DEFAULT_TENANT_ID, get_settings
from ..storage.base import Storage
from .connectors import imap
from .ingest import ingest_email
from .processor import process_email

logger = logging.getLogger("snajp-support.poller")

# Kända leverantörer behöver ingen värd i databasen.
PROVIDER_HOSTS = {
    "gmail": "imap.gmail.com",
    "outlook": "outlook.office365.com",
}

#: Adressdomän → (provider-värde i ss_mailboxes, IMAP-värd). Självbetjänings-
#: kopplingen slår upp värden ur kundens egen adress — kunden ska skriva sitt
#: app-lösenord, inte veta vad en IMAP-värd är. iCloud får provider 'imap'
#: (schemats check-constraint listar gmail/outlook/imap/mock) med värden
#: utskriven på raden.
DOMAN_TILL_IMAP: dict[str, tuple[str, str]] = {
    "gmail.com": ("gmail", "imap.gmail.com"),
    "googlemail.com": ("gmail", "imap.gmail.com"),
    "outlook.com": ("outlook", "outlook.office365.com"),
    "hotmail.com": ("outlook", "outlook.office365.com"),
    "hotmail.se": ("outlook", "outlook.office365.com"),
    "live.com": ("outlook", "outlook.office365.com"),
    "live.se": ("outlook", "outlook.office365.com"),
    "msn.com": ("outlook", "outlook.office365.com"),
    "icloud.com": ("imap", "imap.mail.me.com"),
    "me.com": ("imap", "imap.mail.me.com"),
    "mac.com": ("imap", "imap.mail.me.com"),
}


def imap_for_adress(address: str) -> tuple[str, str] | None:
    """(provider, imap_host) för en mejladress, eller None för okänd domän."""
    doman = address.rsplit("@", 1)[-1].strip().lower()
    return DOMAN_TILL_IMAP.get(doman)


def password_env_name(tenant_slug: str) -> str:
    """IMAP_PASSWORD_LIVRUSTNING för tenanten 'livrustning'."""
    return f"IMAP_PASSWORD_{tenant_slug.upper().replace('-', '_')}"


def losenord_for(mailbox: dict, tenant_slug: str) -> str:
    """App-lösenordet för en inkorgsrad: env-vägen först, sedan radens
    krypterade kolumn.

    Env vinner med flit — det är vägen vi själva förvaltar (Livrustning), och
    en kund som senare kopplar om samma adress via självbetjäningen ska inte
    tyst kunna skugga den. Dekrypteringen görs här och ingen annanstans:
    klartexten lever bara i anropsögonblicket (migration 077).
    """
    ur_env = os.environ.get(password_env_name(tenant_slug), "")
    if ur_env:
        return ur_env
    token = mailbox.get("secret_enc")
    if not token:
        return ""
    from ..integrationer.hemligheter import dekryptera

    try:
        return dekryptera(token).get("losenord", "")
    except Exception:  # noqa: BLE001 — fel nyckel/skadad rad ska ge "saknas", inte 500
        logger.exception("Kunde inte dekryptera inkorgshemligheten för %s", mailbox.get("address"))
        return ""


def host_for_mailbox(mailbox: dict) -> str | None:
    """IMAP-värden för en inkorgsrad, eller None när den inte går att härleda.

    Publik sedan inkorgs-API:t behöver samma svar som pollern: en rad utan
    värd går inte att synka, och UI:t ska kunna säga det innan kunden trycker
    i stället för efter.
    """
    return mailbox.get("imap_host") or PROVIDER_HOSTS.get(mailbox.get("provider") or "")


#: Kvar under det gamla namnet — modulen anropar sig själv på flera ställen.
_host_for = host_for_mailbox


async def sync_mailbox(
    storage: Storage,
    tenant_id: str,
    tenant_slug: str,
    mailbox: dict,
    *,
    bearbeta: bool = True,
) -> dict:
    """Hämtar (och normalt processar) nya mail för EN inkorg.

    `bearbeta=False` är knappvägen (/api/inbox/sync): mailen hämtas och
    skrivs in så att de SYNS i inkorgen direkt, medan LLM-klassificeringen
    körs i en bakgrundsuppgift av anroparen. Utan den delningen tog en synk
    med några mail långt över proxyns tidsbudget, och kunden fick
    "Assistenten har svårt att nå sin motor" fast backenden arbetade — samma
    klass av fel som testmailsknappen hade (uppmätt 60,3 s där). Pollern
    behåller default True: den har ingen klocka emot sig.

    Svaret bär `email_ids`: de oprocessade radernas id:n, för bakgrunds-
    uppgiften.
    """
    settings = get_settings()

    async def stampla(resultat: dict) -> dict:
        """Varje synkFÖRSÖK stämplar raden: last_sync_at = nu, last_error =
        utfallet. Kolumnerna stod oskrivna i fyra månader — kundens "senaste
        synk" var tom för evigt och ett fel lösenord helt tyst. Stämpeln får
        aldrig fälla synken: resultatet är redan framme, och en trasig
        statistikskrivning är inte skäl att kasta bort det."""
        try:
            await storage.touch_mailbox_sync(
                tenant_id, mailbox["id"], last_error=resultat.get("error")
            )
        except Exception:  # noqa: BLE001
            logger.exception("Kunde inte stämpla synken för %s", mailbox.get("address"))
        return resultat

    host = _host_for(mailbox)
    if not host:
        return await stampla({
            "fetched": 0,
            "processed": 0,
            "error": f"Ingen IMAP-värd angiven för {mailbox['address']} (sätt imap_host).",
        })

    password = losenord_for(mailbox, tenant_slug)
    oauth_ready = bool(
        settings.imap_oauth_client_id
        and settings.imap_oauth_client_secret
        and settings.imap_oauth_refresh_token
    )
    if not password and not oauth_ready:
        # Inte ett fel: kunden har ännu inte lämnat app-lösenord eller OAuth.
        return await stampla({
            "fetched": 0,
            "processed": 0,
            "email_ids": [],
            "error": f"Inget app-lösenord för {mailbox['address']} — koppla om inkorgen under Inställningar → Inkorgar.",
        })

    inbound, error = await imap.fetch_new(
        host, mailbox["address"], password, settings.imap_folder,
        oauth_client_id=settings.imap_oauth_client_id,
        oauth_client_secret=settings.imap_oauth_client_secret,
        oauth_refresh_token=settings.imap_oauth_refresh_token,
        oauth_token_url=settings.imap_oauth_token_url,
    )

    processed = 0
    email_ids: list[str] = []
    for message in inbound:
        email = await ingest_email(storage, tenant_id, message)
        if not email:
            continue
        if bearbeta:
            await process_email(storage, tenant_id, email)
            processed += 1
        else:
            email_ids.append(email["id"])
    return await stampla(
        {"fetched": len(inbound), "processed": processed, "email_ids": email_ids, "error": error}
    )


async def sync_imap_once(storage: Storage, tenant_id: str = DEFAULT_TENANT_ID) -> dict:
    """Enkelinkorgs-synk mot de globala IMAP-inställningarna.

    Behålls för /api/inbox/sync och testerna, som synkar en känd tenant på
    begäran. Den periodiska pollern använder sync_all_mailboxes.
    """
    settings = get_settings()
    oauth_ready = bool(
        settings.imap_oauth_client_id
        and settings.imap_oauth_client_secret
        and settings.imap_oauth_refresh_token
    )
    if not (settings.imap_host and settings.imap_user and (settings.imap_password or oauth_ready)):
        return {"fetched": 0, "processed": 0, "error": "IMAP är inte konfigurerat (IMAP_HOST/USER/PASSWORD)."}

    inbound, error = await imap.fetch_new(
        settings.imap_host, settings.imap_user, settings.imap_password, settings.imap_folder,
        oauth_client_id=settings.imap_oauth_client_id,
        oauth_client_secret=settings.imap_oauth_client_secret,
        oauth_refresh_token=settings.imap_oauth_refresh_token,
        oauth_token_url=settings.imap_oauth_token_url,
    )
    processed = 0
    for message in inbound:
        email = await ingest_email(storage, tenant_id, message)
        if email:
            await process_email(storage, tenant_id, email)
            processed += 1
    return {"fetched": len(inbound), "processed": processed, "error": error}


async def sync_all_mailboxes(storage: Storage) -> list[dict]:
    """Ett varv över samtliga aktiva inkorgar, en tenant i taget."""
    results: list[dict] = []

    for tenant in await storage.list_tenants():
        for mailbox in await storage.list_mailboxes(tenant["id"]):
            if mailbox.get("status") != "active" or mailbox.get("provider") == "mock":
                continue
            try:
                summary = await sync_mailbox(storage, tenant["id"], tenant["slug"], mailbox)
            except Exception as error:  # noqa: BLE001 — en trasig inkorg stoppar inte de andra
                logger.exception("Synk misslyckades för %s", mailbox.get("address"))
                summary = {"fetched": 0, "processed": 0, "error": str(error)}
            results.append({"tenant": tenant["slug"], "address": mailbox["address"], **summary})

    return results


async def run_poller(app_state) -> None:
    settings = get_settings()
    interval = max(settings.inbox_poll_seconds, 30)
    logger.info("Inkorgspolling aktiv: var %s sekund.", interval)
    while True:
        try:
            for summary in await sync_all_mailboxes(app_state.storage):
                if summary.get("error"):
                    logger.warning("Polling %s: %s", summary["address"], summary["error"])
                elif summary["fetched"]:
                    logger.info(
                        "Polling %s: %s nya mail processade.",
                        summary["address"],
                        summary["processed"],
                    )
        except Exception:  # noqa: BLE001 — pollern får aldrig dö
            logger.exception("Oväntat fel i inkorgspollern — fortsätter nästa varv.")
        await asyncio.sleep(interval)
