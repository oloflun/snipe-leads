"""Bakgrundspolling av anslutna inkorgar.

Startas i lifespan om INBOX_POLL_SECONDS > 0 och IMAP-uppgifter finns.
Robust: varje varv fångar alla fel (utgången token, nätverk, OpenAI-timeout)
och loggar dem — tjänsten kraschar aldrig på en trasig inkorg.

Mail som hämtas via IMAP hamnar hos default-tenanten (en riktig inkorg per
tenant kopplas via ss_mailboxes när multi-tenant-drift aktiveras fullt ut).
"""

import asyncio
import logging

from ..config import DEFAULT_TENANT_ID, get_settings
from ..storage.base import Storage
from .connectors import imap
from .ingest import ingest_email
from .processor import process_email

logger = logging.getLogger("snajp-support.poller")


async def sync_imap_once(storage: Storage, tenant_id: str | None = None) -> dict:
    """Hämtar och processar nya mail från IMAP. Returnerar sammanfattning.

    Inkorgen tillhör exakt EN arbetsyta (IMAP_TENANT). Andra tenants — framför
    allt den publika demon — får aldrig dra in riktiga kundmail.
    """
    settings = get_settings()
    owner = settings.imap_tenant_id()
    if tenant_id is None:
        tenant_id = owner
    if tenant_id != owner:
        return {
            "fetched": 0,
            "processed": 0,
            "error": (
                "Den här arbetsytan har ingen kopplad inkorg. Riktiga mail hämtas "
                "bara till pilot-arbetsytan — använd testmail här."
            ),
        }
    if not (settings.imap_host and settings.imap_user and settings.imap_password):
        return {
            "fetched": 0,
            "processed": 0,
            "error": (
                "IMAP är inte konfigurerat på servern (IMAP_HOST/IMAP_USER/"
                "IMAP_PASSWORD saknas i miljövariablerna)."
            ),
        }

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


async def run_poller(app_state) -> None:
    settings = get_settings()
    interval = max(settings.inbox_poll_seconds, 30)
    logger.info("Inkorgspolling aktiv: var %s sekund.", interval)
    while True:
        try:
            # Utan tenant-argument går synken till inkorgens ägare (IMAP_TENANT).
            summary = await sync_imap_once(app_state.storage)
            if summary.get("error"):
                logger.warning("Polling: %s", summary["error"])
            elif summary["fetched"]:
                logger.info("Polling: %s nya mail processade.", summary["processed"])
        except Exception:  # noqa: BLE001 — pollern får aldrig dö
            logger.exception("Oväntat fel i inkorgspollern — fortsätter nästa varv.")
        await asyncio.sleep(interval)
