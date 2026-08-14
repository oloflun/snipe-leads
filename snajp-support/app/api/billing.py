"""Abonnemang och kvot.

Tenanten läser sitt eget abonnemang. Skrivning sker bara från Stripe-webhooken,
som går via master-nyckeln — en kund ska inte kunna sätta sin egen nivå genom
att anropa API:t.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..billing.plans import PLANS, get_plan
from ..billing.quota import check_quota
from .deps import require_master_key, require_tenant
from .schemas import SubscriptionUpdateRequest

router = APIRouter()


@router.get("/api/billing/plans")
async def list_plans(tenant: dict = Depends(require_tenant)) -> dict:
    """Nivåerna som finns. Priser hämtas från Stripe på Next-sidan."""
    return {
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "monthly_responses": plan.monthly_responses,
                "description": plan.description,
            }
            for plan in PLANS
            # Interna nivåer är inget kunden kan välja.
            if plan.id != "intern"
        ]
    }


@router.get("/api/billing/subscription")
async def get_subscription(
    request: Request, tenant: dict = Depends(require_tenant)
) -> dict:
    """Tenantens nivå, status och var den ligger mot sitt tak."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    subscription = await storage.get_subscription(tenant_id)
    quota = await check_quota(storage, tenant_id)
    plan = get_plan(subscription.get("plan_id") if subscription else None)

    return {
        "tenant_name": tenant["tenant_name"],
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "monthly_responses": plan.monthly_responses,
            "description": plan.description,
        },
        "status": (subscription or {}).get("status", "none"),
        "cancel_at_period_end": (subscription or {}).get("cancel_at_period_end", False),
        "current_period_end": (subscription or {}).get("current_period_end"),
        "stripe_customer_id": (subscription or {}).get("stripe_customer_id"),
        "quota": quota,
    }


@router.put("/api/billing/subscription")
async def update_subscription(
    request: Request,
    payload: SubscriptionUpdateRequest,
    _master: dict = Depends(require_master_key),
) -> dict:
    """Synk från Stripe-webhooken. Kräver master-nyckel.

    Kunden kan alltså inte uppgradera sig själv genom att anropa API:t — nivån
    ändras bara när Stripe säger att den gjort det.
    """
    storage = request.app.state.storage

    tenant_id = payload.tenant_id
    if not tenant_id and payload.stripe_customer_id:
        tenant_id = await storage.find_tenant_by_stripe_customer(payload.stripe_customer_id)
    if not tenant_id:
        raise HTTPException(
            status_code=404,
            detail="Hittar ingen arbetsyta för det här abonnemanget.",
        )

    record = await storage.upsert_subscription(
        tenant_id,
        plan_id=payload.plan_id,
        status=payload.status,
        stripe_customer_id=payload.stripe_customer_id,
        stripe_subscription_id=payload.stripe_subscription_id,
        current_period_start=payload.current_period_start,
        current_period_end=payload.current_period_end,
        cancel_at_period_end=payload.cancel_at_period_end,
    )
    return {"updated": True, "tenant_id": tenant_id, "subscription": record}
