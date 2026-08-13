"""Tenants & API-nycklar: onboarding av kundföretag (master-nyckel krävs).

POST /api/keys skapar (eller återanvänder) en tenant och utfärdar en nyckel
kopplad till den. Nyckeln returneras i klartext EN gång; endast sha256-hashen
sparas. Varje nyckel ger enbart åtkomst till sin egen tenants data.
"""

import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request

from .deps import require_master_key, require_tenant
from .schemas import CreateKeyRequest, CreateOwnKeyRequest

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
        new_tenant["id"],
        tenant_name=new_tenant["name"],
        raw_key=raw_key,
        label=payload.label,
    )
    return {
        "api_key": raw_key,
        "tenant_id": new_tenant["id"],
        "tenant_name": new_tenant["name"],
        "tenant_slug": new_tenant["slug"],
        "key_prefix": record["key_prefix"],
        "note": "Spara nyckeln nu — den visas aldrig igen.",
    }


# -- Self-service: kunden hanterar sina egna nycklar -------------------------


@router.get("/api/keys")
async def list_keys(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    keys = await request.app.state.storage.list_api_keys(tenant["tenant_id"])
    return {"tenant_name": tenant["tenant_name"], "keys": keys}


@router.post("/api/keys/self", status_code=201)
async def create_own_key(
    request: Request, payload: CreateOwnKeyRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Ny nyckel till den EGNA tenanten — ingen master-nyckel, inget seed-script.

    tenant_id kommer från den anropande nyckeln, så en kund kan bara utfärda
    nycklar till sin egen arbetsyta.
    """
    raw_key = f"snajp_live_{secrets.token_hex(16)}"
    record = await request.app.state.storage.create_api_key(
        tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        raw_key=raw_key,
        label=payload.label,
    )
    return {
        "api_key": raw_key,
        "key_prefix": record["key_prefix"],
        "id": record["id"],
        "label": payload.label,
        "note": "Spara nyckeln nu — den visas aldrig igen.",
    }


@router.delete("/api/keys/{key_id}")
async def revoke_key(
    request: Request, key_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    revoked = await request.app.state.storage.revoke_api_key(tenant["tenant_id"], key_id)
    if not revoked:
        # 404, inte 403: en nyckel hos en annan tenant ska inte gå att bekräfta.
        raise HTTPException(status_code=404, detail="Nyckeln finns inte.")
    return {"revoked": True, "id": key_id}
