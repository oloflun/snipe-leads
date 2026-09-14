"""Ingest: spara råmail + bilagor med dedupe och beslutslogg."""

import logging
from datetime import datetime
from typing import Any

from ..storage.base import Storage
from .models import InboundEmail

logger = logging.getLogger("snajp-support.ingest")


def _received_at_for_storage(value: str | datetime | None) -> datetime | None:
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


async def ingest_email(
    storage: Storage, tenant_id: str, inbound: InboundEmail, *, is_test: bool = False
) -> dict[str, Any] | None:
    """Sparar ett inkommande mail. Returnerar mailraden, eller None vid dublett."""
    email = await storage.save_email(
        tenant_id,
        provider=inbound.provider,
        provider_message_id=inbound.provider_message_id,
        from_email=inbound.from_email,
        from_name=inbound.from_name,
        subject=inbound.subject,
        body_text=inbound.body_text,
        received_at=_received_at_for_storage(inbound.received_at),
        is_test=is_test or inbound.provider == "mock",
    )
    if email is None:
        logger.info("Dublett hoppad: %s", inbound.provider_message_id)
        return None

    for attachment in inbound.attachments:
        await storage.add_attachment(
            tenant_id,
            email_id=email["id"],
            filename=attachment.filename,
            content_type=attachment.content_type,
            data_url=attachment.data_url,
            is_image=attachment.is_image,
            size_bytes=attachment.size_bytes,
        )

    await storage.log_decision(
        tenant_id,
        email_id=email["id"],
        event="received",
        detail={
            "provider": inbound.provider,
            "from": inbound.from_email,
            "subject": inbound.subject,
            "attachments": len(inbound.attachments),
        },
    )
    return email
