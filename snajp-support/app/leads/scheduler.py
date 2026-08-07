"""Del J / Genomförandeordning steg 11: bakgrundskö och schemaläggare.

Speglar app/email_pipeline/poller.py:s mönster exakt (samma
asyncio.create_task-loop, samma "aldrig krascha tjänsten"-princip) i
stället för att lägga till APScheduler som ett nytt beroende för samma
jobb — kodbasen har redan en beprövad periodisk bakgrundsloop.

INV-SEC-004: modellen kan bara köa. process_due_item() är den ENDA
kodvägen i hela tjänsten som får sätta ett send_queue-item till 'sent'.
Grindarna körs igen här (app/leads/send_decision.decide_send_action) —
en köad tid kan ha passerat fönstret sedan den köades.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ..config import get_settings
from ..storage.base import Storage
from .send_decision import decide_send_action
from .send_provider import SendProvider, get_send_provider

logger = logging.getLogger("snajp-support.leads-scheduler")


async def process_due_item(
    storage: Storage, tenant_id: str, item: dict, provider: SendProvider, *, now: datetime
) -> str:
    """Returnerar 'sent' | 'requeued' | 'blocked'."""
    thread = await storage.get_outreach_thread(tenant_id, item["thread_id"])
    message = (
        await storage.get_pending_outreach_message(tenant_id, item["thread_id"]) if thread else None
    )
    decision = decide_send_action(now=now, thread=thread, message=message)

    if decision.action == "send":
        await provider.send(
            to=thread.get("prospect_email", "okänd"),
            subject=message.get("subject", ""),
            body=message["body"],
        )
        await storage.mark_outreach_message_sent(tenant_id, message["id"], now)
        await storage.update_send_queue_status(
            tenant_id, item["id"], status="sent", gate_checks={"decision": decision.reason}
        )
        return "sent"

    if decision.action == "block":
        await storage.update_send_queue_status(
            tenant_id, item["id"], status="blocked", gate_checks={"decision": decision.reason}
        )
        return "blocked"

    # requeue: status förblir 'queued' — fångas upp igen nästa gång fönstret är öppet.
    await storage.update_send_queue_status(
        tenant_id, item["id"], status="queued", gate_checks={"decision": decision.reason}
    )
    return "requeued"


async def process_all_due(storage: Storage, provider: SendProvider) -> list[dict]:
    now = datetime.now(timezone.utc)
    results: list[dict] = []
    for tenant in await storage.list_tenants():
        for item in await storage.list_due_send_queue(tenant["id"], now):
            try:
                outcome = await process_due_item(storage, tenant["id"], item, provider, now=now)
            except Exception:  # noqa: BLE001 — en trasig post stoppar inte de andra
                logger.exception("send_queue-post %s misslyckades oväntat", item.get("id"))
                outcome = "error"
            results.append({"tenant": tenant["slug"], "item_id": item.get("id"), "outcome": outcome})
    return results


async def run_send_scheduler(app_state) -> None:
    settings = get_settings()
    interval = max(settings.send_queue_poll_seconds, 30)
    provider = get_send_provider()
    logger.info("send_queue-schemaläggare aktiv: var %s sekund.", interval)
    while True:
        try:
            for result in await process_all_due(app_state.storage, provider):
                if result["outcome"] != "requeued":
                    logger.info(
                        "send_queue %s (%s): %s",
                        result["item_id"],
                        result["tenant"],
                        result["outcome"],
                    )
        except Exception:  # noqa: BLE001 — schemaläggaren får aldrig dö
            logger.exception("Oväntat fel i send_queue-schemaläggaren — fortsätter nästa varv.")
        await asyncio.sleep(interval)
