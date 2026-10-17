"""Arbetsytans siffror som underlag för hjälpchatten (2026-10-05).

## Vad det här är

När en INLOGGAD företagskund chattar i sin egen arbetsyta (Testchatt-fliken)
ska agenten kunna svara på "hur många leads fick vi den här veckan?" och
"hur mycket av budgeten är kvar?". Blocket här byggs ur samma källor som
Översikten och Analysvyn — `weekly_analytics` (en SQL-fråga),
granskningskön och supportbudgeten — och läggs i case_context plus i
faktagrindens källor, så att siffrorna får citeras utan att grinden
stryker dem.

## Gating — varför blocket inte byggs för alla

Flaggan `arbetsyta` sätts ENBART av den autentiserade testchatt-routen i
Next (app/api/snajp-support/testchatt/route.ts, tenant ur sessionen) och
STRIPPAS av den publika chat-routen. En slutkund i kundens publika chatt
ska aldrig kunna fråga ut företagets interna siffror. Ett direktanrop mot
backenden kräver tenantens API-nyckel, som redan ger hela API:t.

Fail-open: fallerar någon källa byggs blocket utan den delen, och
fallerar allt blir blocket tomt — siffrorna är en bonus, svaret är jobbet.
"""

from __future__ import annotations

import logging
from typing import Any

from ..budget import budget_for

logger = logging.getLogger("snajp-support.arbetsyta_siffror")


def _veckorad(vecka: dict[str, Any], etikett: str) -> str:
    return (
        f"- {etikett} (v. {vecka.get('week', '?')}): "
        f"{vecka.get('sent', 0)} utskickade mejl, {vecka.get('replies', 0)} svar, "
        f"{vecka.get('leads_runs', 0)} leads-körningar, "
        f"{vecka.get('tickets', 0)} supportärenden "
        f"(varav {vecka.get('escalated', 0)} eskalerade, "
        f"{vecka.get('resolved', 0)} lösta), "
        f"{vecka.get('support_runs', 0)} supportkörningar"
    )


async def bygg_sifferblock(storage: Any, tenant_id: str) -> str:
    """Ett kompakt textblock med arbetsytans egna nyckeltal, eller ""."""
    rader: list[str] = []

    try:
        analys = await storage.weekly_analytics(tenant_id, weeks=2)
        veckor = analys.get("weeks") or []
        if veckor:
            rader.append(_veckorad(veckor[-1], "Den här veckan"))
        if len(veckor) >= 2:
            rader.append(_veckorad(veckor[-2], "Förra veckan"))
    except Exception:  # noqa: BLE001 — siffrorna är en bonus, svaret är jobbet
        logger.exception("weekly_analytics föll — sifferblocket byggs utan veckorna")

    try:
        granskningsko = await storage.list_review_queue(tenant_id, limit=100)
        rader.append(
            f"- Utkast som väntar på granskning i leads-kön: {len(granskningsko)}"
            + (" (minst)" if len(granskningsko) == 100 else "")
        )
    except Exception:  # noqa: BLE001
        logger.exception("list_review_queue föll — sifferblocket byggs utan kön")

    try:
        tenant = await storage.get_tenant(tenant_id) or {}
        tak = budget_for(tenant.get("slug"))
        if tak > 0:
            forbrukat = await storage.sum_support_tokens(tenant_id, hours=24)
            rader.append(
                f"- Supportagentens dygnsbudget: {forbrukat} av {tak} tokens "
                f"förbrukade senaste dygnet"
            )
    except Exception:  # noqa: BLE001
        logger.exception("budgetläsningen föll — sifferblocket byggs utan budget")

    if not rader:
        return ""
    return (
        "## Arbetsytans siffror\n"
        "Kontoinnehavarens egna nyckeltal, hämtade ur systemet just nu. Du "
        "får återge dem för den här användaren. Räkna inte om dem och "
        "extrapolera inte — saknas en siffra, säg det och hänvisa till "
        "Översikten eller Analys-fliken i arbetsytan.\n"
        + "\n".join(rader)
    )
