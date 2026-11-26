"""Hjälprutans samtal: kundens samtal med Snajps egen supportagent.

Plan: docs/PLAN-HJALPRUTAN-2026-11-25.md, del 2.

Hjälpen har en egen kund i systemet (`Settings.hjalp_tenant_slug`, förvalt
"snajp-hjalp"), skild från "snajp" som marknadssidans anonyma demo använder.
Next-servern anropar med hjälpens nyckel och bygger avsändaren ur sessionen:
`<användar-id>@kund.snajp.se`. Den domänen avvisas av den anonyma
`/api/chat/samtal` (chat.py), och den här vägen godtar BARA den. En besökare
på marknadssidan kan alltså inte läsa en kunds hjälpsamtal ens med rätt
adress, och hjälpens nyckel kan inte läsa marknadssidans sessioner.

`require_hjalp_tenant` är grinden för varje väg som bara hjälpens nyckel får
nå (det här samtalet och plattformsärendena). En annan tenants nyckel får 404,
inte 403: en väg man inte har ska inte gå att skilja från en som inte finns
(samma resonemang som deps.kraev_uuid).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from .deps import require_tenant
from .schemas import SamtalRequest

router = APIRouter()

#: Avsändardomänen för en inloggad kunds hjälpsamtal. Sätts av Next-servern
#: ur sessionen (aldrig av klienten) och avvisas av den anonyma vägen.
KUNDDOMAN = "@kund.snajp.se"


async def require_hjalp_tenant(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Nyckeln måste höra till hjälpens kund, annars 404."""
    rad = await request.app.state.storage.get_tenant(tenant["tenant_id"])
    if not rad or rad.get("slug") != get_settings().hjalp_tenant_slug:
        raise HTTPException(status_code=404, detail="Sidan finns inte.")
    return tenant


@router.post("/api/hjalp/samtal")
async def hamta_hjalpsamtal(
    request: Request, payload: SamtalRequest, tenant: dict = Depends(require_hjalp_tenant)
) -> dict:
    """Hjälpsamtalet för en inloggad användare: läget och meddelandena.

    Systern till `POST /api/chat/samtal` (chat.py) med samma svarsform, men
    för den inloggade ytan: historiken hämtas från servern, så samtalet finns
    kvar efter en omladdning och på andra enheter.
    """
    from ..agent import overlamning
    from ..agent.support_agent import ar_overlamnat

    email = payload.customer_email.strip().lower()
    if not email.endswith(KUNDDOMAN):
        raise HTTPException(status_code=422, detail="Bara hjälpsamtal kan läsas tillbaka här.")
    storage = request.app.state.storage
    kund = await storage.find_customer(tenant["tenant_id"], email=email)
    if not kund:
        return {"overlamnad": False, "meddelanden": []}
    samtal = await storage.get_chat_state(tenant["tenant_id"], kund["id"])
    rader = await overlamning.samtalsutskrift(storage, tenant["tenant_id"], kund["id"])
    return {
        "overlamnad": ar_overlamnat(samtal),
        "meddelanden": [
            {"id": r["id"], "author": r["author"], "content": r["content"], "created_at": r["created_at"]}
            for r in overlamning.efter(rader, payload.efter)
        ],
    }
