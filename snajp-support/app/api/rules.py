"""Regler per fack: auto (skicka direkt), draft (kräver godkännande), escalate."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import CATEGORIES, CATEGORY_LABELS
from .deps import require_tenant
from .schemas import CategoryRuleRequest

router = APIRouter()


@router.get("/api/rules")
async def get_rules(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    rules = await request.app.state.storage.get_category_rules(tenant["tenant_id"])
    return {
        "rules": [
            {"category": c, "label": CATEGORY_LABELS[c], "mode": rules.get(c, "draft")}
            for c in CATEGORIES
        ]
    }


@router.put("/api/rules")
async def set_rule(
    request: Request, payload: CategoryRuleRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    if payload.category not in CATEGORIES:
        raise HTTPException(status_code=422, detail="Okänt fack.")
    await request.app.state.storage.set_category_rule(
        tenant["tenant_id"], payload.category, payload.mode
    )
    await request.app.state.storage.log_decision(
        tenant["tenant_id"], email_id=None, event="rule_changed",
        detail={"category": payload.category, "mode": payload.mode},
    )
    return {"category": payload.category, "mode": payload.mode}
