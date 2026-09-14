"""Tenants & API-nycklar: onboarding av kundföretag (master-nyckel krävs).

POST /api/keys skapar (eller återanvänder) en tenant och utfärdar en nyckel
kopplad till den. Nyckeln returneras i klartext EN gång; endast sha256-hashen
sparas. Varje nyckel ger enbart åtkomst till sin egen tenants data.
"""

import logging
import re
import secrets

from fastapi import APIRouter, Depends, Request

from .deps import require_master_key
from .schemas import CreateKeyRequest

router = APIRouter()

logger = logging.getLogger("snajp-support.keys")

#: Testarbetsytornas slugmönster. Måste stämma med regexen i migration 040
#: (`public.link_test_tenant`) och med `arTestkundSlug` i lib/tenants/index.ts.
TESTKUND_PREFIX = "testkund-"


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
    # En testarbetsyta ska ha en fungerande agent från första minuten.
    #
    # Utan det här får en ny tenant sin första artikel först när någon trycker
    # "Hämta testmail" — altså aldrig för den som börjar i leads-vyn eller i
    # chatten. Grundningsregeln (processor.py steg 2) kräver minst en träff, en
    # tom bas ger noll, och följden är att agenten eskalerar allt. Det ser ut som
    # en trasig produkt och är i själva verket en tom hylla.
    #
    # BARA för testtenants. KB_ARTICLES är Nordlys Handels e-handelsartiklar; i
    # en riktig kunds bas vore de ett ANNAT bolags villkor, presenterade som
    # kundens egna — precis den korsning egna tenants finns för att stoppa.
    # Riktiga kunder seedas ur sin egen modul i app/tenants/ via seed_kb.py.
    kb_seeded = 0
    if new_tenant["slug"].startswith(TESTKUND_PREFIX):
        try:
            from ..scripts.seed_kb import ensure_tenant_kb

            kb_seeded = await ensure_tenant_kb(storage, new_tenant["id"])
        except Exception as error:  # noqa: BLE001 — en tom bas fäller inte nyckeln
            logger.warning("Kunde inte seeda KB för %s (%s).", new_tenant["slug"], error)

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
        "kb_seeded": kb_seeded,
        "note": "Spara nyckeln nu — den visas aldrig igen.",
    }
