"""Tenantens egna inställningar och förbrukning (self-service).

Allt här är skopat till den anropande nyckelns tenant — det finns ingen väg att
be om någon annans inställningar, eftersom tenant_id kommer från nyckeln och
aldrig från klienten.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import CATEGORIES
from .deps import require_tenant
from .schemas import TenantSettingsRequest

router = APIRouter()


def _public_view(tenant: dict) -> dict:
    """Fälten en kund får se om sin egen tenant."""
    return {
        "id": tenant.get("id"),
        "slug": tenant.get("slug"),
        "name": tenant.get("name"),
        "company_name": tenant.get("company_name"),
        "tone": tenant.get("tone"),
        "system_prompt_extra": tenant.get("system_prompt_extra"),
        "active": tenant.get("active", True),
        "created_at": tenant.get("created_at"),
        "updated_at": tenant.get("updated_at"),
    }


@router.get("/api/tenant")
async def get_tenant(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    record = await request.app.state.storage.get_tenant(tenant["tenant_id"])
    if not record:
        raise HTTPException(status_code=404, detail="Arbetsytan finns inte.")
    return _public_view(record)


@router.put("/api/tenant")
async def update_tenant(
    request: Request,
    payload: TenantSettingsRequest,
    tenant: dict = Depends(require_tenant),
) -> dict:
    record = await request.app.state.storage.update_tenant(
        tenant["tenant_id"],
        name=payload.name,
        company_name=payload.company_name,
        tone=payload.tone,
        system_prompt_extra=payload.system_prompt_extra,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Arbetsytan finns inte.")
    return _public_view(record)


@router.get("/api/usage")
async def get_usage(
    request: Request, days: int = 30, tenant: dict = Depends(require_tenant)
) -> dict:
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail="days måste vara mellan 1 och 365.")
    usage = await request.app.state.storage.get_usage(tenant["tenant_id"], days=days)
    return {"tenant_name": tenant["tenant_name"], **usage}


@router.get("/api/onboarding/status")
async def onboarding_status(
    request: Request, tenant: dict = Depends(require_tenant)
) -> dict:
    """Vad som återstår innan arbetsytan är redo att svara kunder.

    Tänkt att driva en checklista i UI:t, så en ny kund ser exakt vad som
    saknas i stället för att upptäcka det när första mailet eskaleras.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    record = await storage.get_tenant(tenant_id) or {}
    articles = await storage.list_kb(tenant_id)

    from ..kb_templates import PLACEHOLDER_PREFIX

    placeholders = [
        a for a in articles if a.get("content", "").startswith(PLACEHOLDER_PREFIX)
    ]
    rules = await storage.get_category_rules(tenant_id)

    steps = [
        {
            "id": "kb",
            "label": "Fyll kunskapsbasen",
            "done": len(articles) > len(placeholders),
            "detail": f"{len(articles)} artiklar, varav {len(placeholders)} platshållare.",
        },
        {
            "id": "placeholders",
            "label": "Ersätt platshållartexterna",
            "done": not placeholders,
            "detail": (
                "Platshållare eskaleras alltid i stället för att användas som svar."
                if placeholders
                else "Klart."
            ),
        },
        {
            "id": "profile",
            "label": "Beskriv verksamheten och tonen",
            "done": bool(record.get("system_prompt_extra")),
            "detail": "Styr hur agenten presenterar er och vilken ton den håller.",
        },
    ]
    return {
        "tenant_name": tenant["tenant_name"],
        "ready": all(step["done"] for step in steps),
        "steps": steps,
        "categories": list(CATEGORIES),
        "rules": rules,
    }
