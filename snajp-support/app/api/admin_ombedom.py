"""Ombedömning av sparade Iris-leads, bakom master-nyckeln.

## Varför

Bedömningsreglerna skärptes 2026-10-06: varje lead kräver ett belagt behov av
det kunden säljer (`bedomning._produktmatch_rad`), och ett obelagt måste-krav
fäller. Nya körningar följer reglerna, men leads som redan står i listan
bedömdes med de gamla och syns kvar. Ombedömningen kör om researchen för dem
i samma jobbkö som kundens "Processa om", så de bedöms med exakt samma kod
som en ny körning. Ett bolag som inte klarar de nya reglerna blir nivå C och
försvinner ur listan (raden står kvar i databasen för dedupliceringen).

## Vad som rörs

Bara leads ur Iris eller testkörningar, med nivå A eller B och status Ny
eller Redo. Ett lead kunden redan arbetar med (kontaktad, svarat, möte, vunnen,
förlorad) rörs aldrig: att det plötsligt försvann ur listan vore värre än en
gammal bedömning. Endast research, aldrig utkast.

## Leads som föll för att hämtningen misslyckades

Ett lead vars sidor inte gick att hämta vid ombedömningen blir nivå C med
raden "Källmaterial" (bedomning.bedom, har_underlag=False) — utan att någon
bedömning gjorts. Uppmätt 2026-10-06: ScrapeGraph-krediten var slut, och 13
av Alunix 18 leads föll så. `utan_underlag=true` tar med just de, så att de
kan bedömas om när hämtningen fungerar igen. Ett lead som Iris faktiskt
bedömt och valt bort tas aldrig med.

Torrkörning som standard (samma mönster som admin_konvertera.py). Ligger inte
i admin.py: den filen skriver inte.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .deps import kraev_uuid, require_master_key

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])

#: Ursprung vars leads visas för kunden som Iris-fynd.
URSPRUNG = ("iris", "test")
#: Status där kunden ännu inte agerat på leadet.
STATUS = ("new", "ready")
#: Tak per anrop: jobbkön är sekventiell och budgeten per dygn.
MAX_PER_ANROP = 100


class OmbedomRequest(BaseModel):
    apply: bool = False
    utan_underlag: bool = False


def foll_utan_underlag(p: dict) -> bool:
    """Nivå C enbart för att inget källmaterial gick att hämta."""
    return p.get("niva") == "C" and any(
        isinstance(r, dict) and r.get("nyckel") == "underlag" and r.get("etikett") == "Källmaterial"
        for r in p.get("score_breakdown") or []
    )


def ska_ombedomas(p: dict, *, utan_underlag: bool = False) -> bool:
    if p.get("origin") not in URSPRUNG or p.get("status") not in STATUS:
        return False
    if utan_underlag:
        return foll_utan_underlag(p)
    return p.get("niva") in ("A", "B")


@router.post("/tenants/{tenant_id}/leads-ombedom")
async def ombedom_leads(request: Request, tenant_id: str, payload: OmbedomRequest) -> dict:
    """Torrkör som default: listar vad som skulle bedömas om. apply=true köar
    researchjobben (scope research, inga utkast)."""
    kraev_uuid(tenant_id, "Kunden")
    storage = request.app.state.storage
    kund = await storage.get_tenant(tenant_id)
    if not kund:
        raise HTTPException(status_code=404, detail="Kunden finns inte.")

    kandidater = [
        p for p in await storage.list_prospects(tenant_id, limit=500)
        if ska_ombedomas(p, utan_underlag=payload.utan_underlag)
    ]
    svar: dict = {
        "antal": len(kandidater),
        "leads": [
            {"id": str(p["id"]), "company_name": p.get("company_name"), "niva": p.get("niva"),
             "status": p.get("status"), "origin": p.get("origin")}
            for p in kandidater
        ],
        "jobb": [],
    }
    if not payload.apply or not kandidater:
        return svar

    from .leads import _kraev_leads_budget, _lagg_prospektjobb, _require_live_llm

    _require_live_llm()
    await _kraev_leads_budget(storage, tenant_id)
    tenant = {"tenant_id": tenant_id, "tenant_name": kund.get("name") or kund.get("slug") or tenant_id}
    valda = kandidater[:MAX_PER_ANROP]
    for ursprung in URSPRUNG:
        grupp = [p for p in valda if p.get("origin") == ursprung]
        if grupp:
            svar["jobb"] += await _lagg_prospektjobb(
                request.app.state, tenant, grupp, scope="research", overrides=None,
                is_test=ursprung == "test", limit=len(grupp),
            )

    await storage.log_platform_event(
        level="info",
        source="admin.leads_ombedom",
        message=f"Ombedömning av {len(svar['jobb'])} Iris-leads köad: {tenant['tenant_name']}.",
        tenant_id=tenant_id,
        detail={"prospekt": [str(p["id"]) for p in valda]},
    )
    return svar
