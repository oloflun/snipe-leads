"""Kvotkontroll per tenant.

Två regler styr designen:

1. **En slut kvot får aldrig se ut som ett fel.** Kunden ska få ett begripligt
   svenskt besked om att abonnemanget är förbrukat — inte en krasch, inte ett
   tomt svar, och inte ett påhittat svar från agenten.
2. **En trasig kvotkontroll får aldrig blockera ett svar.** Går uppslaget inte
   att göra (databasen nere, tabellen inte migrerad ännu) släpper vi igenom och
   loggar. Att stoppa en betalande kunds support för att vår mätning krånglar
   vore värre än att råka ge några svar för mycket.
"""

import logging
from datetime import datetime, timezone

from ..storage.base import Storage
from .plans import quota_state

logger = logging.getLogger("snajp-support.quota")

QUOTA_MESSAGE = (
    "Tack för att du hör av dig! Just nu kan jag tyvärr inte svara automatiskt, "
    "eftersom vårt supportabonnemang nått sin gräns för den här perioden. "
    "Ditt ärende är registrerat och en kollega återkommer så snart som möjligt."
)


def _period_start(subscription: dict | None) -> str:
    """Början på innevarande faktureringsperiod.

    Utan abonnemangsrad (eller utan period från Stripe) räknas kalendermånaden,
    vilket är det kunden intuitivt förväntar sig.
    """
    if subscription and subscription.get("current_period_start"):
        return str(subscription["current_period_start"])
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


async def check_quota(storage: Storage, tenant_id: str) -> dict:
    """Var tenanten står just nu.

    Returnerar alltid ett användbart svar. Vid fel: `exceeded=False` och
    `degraded=True`, så anroparen släpper igenom.
    """
    try:
        subscription = await storage.get_subscription(tenant_id)
        used = await storage.count_responses_since(tenant_id, _period_start(subscription))
        state = quota_state(subscription.get("plan_id") if subscription else None, used)
        state["status"] = (subscription or {}).get("status", "none")
        state["period_start"] = _period_start(subscription)
        state["degraded"] = False
        return state
    except Exception as error:  # noqa: BLE001 — mätfel får aldrig stoppa support
        logger.warning("Kunde inte läsa kvoten för tenant %s: %s", tenant_id, error)
        return {
            "plan_id": None,
            "plan_name": None,
            "used": 0,
            "cap": None,
            "remaining": None,
            "ratio": 0.0,
            "warn": False,
            "exceeded": False,
            "status": "unknown",
            "degraded": True,
        }


def quota_exceeded_result(state: dict) -> dict:
    """Svarsobjekt när kvoten är slut — samma form som agentens vanliga svar.

    Ärendet skapas medvetet INTE här: kunden ska höras av, men vi lägger inte på
    fler rader hos en tenant som redan slagit i taket. Eskaleringsflaggan gör att
    det syns i dashboarden att en människa behöver ta över.
    """
    return {
        "reply": QUOTA_MESSAGE,
        "ticket_id": None,
        "customer_id": None,
        "category": "ovrigt",
        "category_label": "Övrigt",
        "sentiment": None,
        "escalated": True,
        "escalation_reason": "Abonnemangets svarskvot är förbrukad för perioden.",
        "kb_sources": [],
        "returning_customer": False,
        "simulation": False,
        "quota_exceeded": True,
        "quota": state,
    }
