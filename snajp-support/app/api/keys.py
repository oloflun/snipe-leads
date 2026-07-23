"""Tenants & API-nycklar: onboarding av kundföretag (master-nyckel krävs).

POST /api/keys skapar (eller återanvänder) en tenant och utfärdar en nyckel
kopplad till den. Nyckeln returneras i klartext EN gång; endast sha256-hashen
sparas. Varje nyckel ger enbart åtkomst till sin egen tenants data.
"""

import re
import secrets

from fastapi import APIRouter, Depends, Request

from .deps import require_master_key
from .schemas import CreateKeyRequest

router = APIRouter()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("å", "a").replace("ä", "a").replace("ö", "o"))
    return slug.strip("-") or "tenant"


@router.post("/api/keys", status_code=201)
async def create_key(
    request: Request, payload: CreateKeyRequest, tenant: dict = Depends(require_master_key)
) -> dict:
    storage = request.app.state.storage
    new_tenant = await storage.create_tenant(
        slug=payload.slug or _slugify(payload.tenant_name), name=payload.tenant_name
    )
    raw_key = f"snajp_live_{secrets.token_hex(16)}"
    record = await storage.create_api_key(
        new_tenant["id"], tenant_name=new_tenant["name"], raw_key=raw_key
    )
    return {
        "api_key": raw_key,
        "tenant_id": new_tenant["id"],
        "tenant_name": new_tenant["name"],
        "tenant_slug": new_tenant["slug"],
        "key_prefix": record["key_prefix"],
        "note": "Spara nyckeln nu — den visas aldrig igen.",
    }
