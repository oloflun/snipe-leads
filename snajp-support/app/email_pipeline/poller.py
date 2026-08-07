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


def password_env_name(tenant_slug: str) -> str:
    """IMAP_PASSWORD_LIVRUSTNING för tenanten 'livrustning'."""
    return f"IMAP_PASSWORD_{tenant_slug.upper().replace('-', '_')}"


def _host_for(mailbox: dict) -> str | None:
    return mailbox.get("imap_host") or PROVIDER_HOSTS.get(mailbox.get("provider") or "")


async def sync_mailbox(storage: Storage, tenant_id: str, tenant_slug: str, mailbox: dict) -> dict:
    """Hämtar och processar nya mail för EN inkorg."""
    settings = get_settings()

    host = _host_for(mailbox)
    if not host:
        return {
            "fetched": 0,
            "processed": 0,
            "error": f"Ingen IMAP-värd angiven för {mailbox['address']} (sätt imap_host).",
        }

    password = os.environ.get(password_env_name(tenant_slug))
    if not password:
        # Inte ett fel: kunden har ännu inte lämnat sitt app-lösenord. Raden får
        # ligga kvar och pollern tar den så fort nyckeln finns.
        return {
            "fetched": 0,
            "processed": 0,
            "error": f"{password_env_name(tenant_slug)} saknas — hoppar över {mailbox['address']}.",
        }

    inbound, error = await imap.fetch_new(host, mailbox["address"], password, settings.imap_folder)

    processed = 0
    for message in inbound:
        email = await ingest_email(storage, tenant_id, message)
        if email:
            await process_email(storage, tenant_id, email)
            processed += 1
    return {"fetched": len(inbound), "processed": processed, "error": error}


async def sync_imap_once(storage: Storage, tenant_id: str = DEFAULT_TENANT_ID) -> dict:
    """Enkelinkorgs-synk mot de globala IMAP-inställningarna.

    Behålls för /api/inbox/sync och testerna, som synkar en känd tenant på
    begäran. Den periodiska pollern använder sync_all_mailboxes.
    """
    settings = get_settings()
    if not (settings.imap_host and settings.imap_user and settings.imap_password):
        return {"fetched": 0, "processed": 0, "error": "IMAP är inte konfigurerat (IMAP_HOST/USER/PASSWORD)."}

    inbound, error = await imap.fetch_new(
        settings.imap_host, settings.imap_user, settings.imap_password, settings.imap_folder
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
