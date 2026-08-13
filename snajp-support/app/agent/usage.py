"""Förbrukningsmätning per tenant — underlag för tak och fakturering.

Loggning får ALDRIG fälla ett kundsvar. Ett mätvärde som inte kan sparas är
irriterande; ett svar som inte når kunden för att mätningen kraschade är ett
driftfel. Därför sväljs alla fel här och loggas som varning.

Simuleringsläget loggas också, med simulated=True och noll tokens — annars ser
ett konto som testkörts hela veckan ut som orört.
"""

import logging
from typing import Any

from ..config import get_settings
from ..storage.base import Storage

logger = logging.getLogger("snajp-support.usage")


async def log_usage(
    storage: Storage,
    tenant_id: str,
    *,
    kind: str,
    simulated: bool,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    responses: int = 1,
    model: str | None = None,
    ticket_id: str | None = None,
    email_id: str | None = None,
) -> None:
    try:
        await storage.log_usage(
            tenant_id,
            kind=kind,
            model=model or ("simulation" if simulated else get_settings().model),
            simulated=simulated,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            responses=responses,
            ticket_id=ticket_id,
            email_id=email_id,
        )
    except Exception as error:  # noqa: BLE001 — mätning får aldrig fälla svaret
        logger.warning("Kunde inte logga förbrukning för tenant %s: %s", tenant_id, error)


async def log_run_usage(
    storage: Storage,
    tenant_id: str,
    result: Any,
    *,
    kind: str,
    ticket_id: str | None = None,
    email_id: str | None = None,
) -> None:
    """Läser tokens ur ett Agents SDK-resultat (RunResult.context_wrapper.usage)."""
    usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
    await log_usage(
        storage,
        tenant_id,
        kind=kind,
        simulated=False,
        prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
        completion_tokens=getattr(usage, "output_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
        ticket_id=ticket_id,
        email_id=email_id,
    )
