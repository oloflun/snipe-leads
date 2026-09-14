"""Kundregistret — adminfliken Kunder & Data:s läs- och skrivyta.

## Varför en egen fil bredvid admin.py och admin_profil.py

`admin.py` bär regeln "ingen endpoint här skriver", och kundregistret skrivs.
`admin_profil.py` ändrar det som formar FRAMTIDA agentkörningar; det här är
något annat: faktureringsuppgifter och kontaktpersoner, som inte påverkar en
enda körning. Två skrivytor med olika blastradie ska inte dela fil — den som
granskar en ändring i agentinstruktionerna ska inte behöva läsa förbi ett
telefonnummerfält.

## Automatiskt och manuellt, och varför svaret bär en källa per fält

Registerraden (ss_customer_details) är det manuella lagret. Ovanpå den lägger
läsvägen härledda värden: kund-sedan-datumet faller tillbaka på tenantens
skapelsedatum, organisationsnumret på affärskontextens fritextrad från
onboardingen. Varje fält i svaret bär därför `kalla` — "manuell",
"onboarding", "system" eller null (saknas) — så att vyn kan säga VAR ett
värde kom ifrån. Ett faktureringsunderlag där en gissning ser manuellt
bekräftad ut är värre än ett hål.

## Spårning

Varje skrivning loggar en rad i platform_events med kund och fältnamn, samma
mönster som admin_profil.py. Fältens VÄRDEN loggas aldrig — händelseloggen
läses bredare än registret och ska inte bli en andra kopia av det.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request

from ..storage.base import KUNDDATA_FALT
from .deps import kraev_uuid, require_master_key
from .schemas import KontaktRequest, KunddataRequest

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])

#: Onboardingen skriver "Organisationsnummer: 556677-8899" i affärskontexten
#: (lib/actions/onboarding.ts). Testarbetsytors rad ("— (TESTARBETSYTA…)")
#: matchar med flit inte — en testyta har inget orgnr att härleda.
_ORGNR_RAD = re.compile(r"Organisationsnummer:\s*(\d{6}-\d{4})")


async def _hamta_tenant(request: Request, tenant_id: str) -> dict:
    kraev_uuid(tenant_id, "Kunden")
    tenant = await request.app.state.storage.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Kunden finns inte.")
    return tenant


async def _harledd_orgnr(storage, tenant_id: str) -> str | None:
    doc = await storage.get_latest_context_doc(tenant_id, kind="product_marketing")
    if not doc:
        return None
    traff = _ORGNR_RAD.search(doc.get("content") or "")
    return traff.group(1) if traff else None


@router.get("/tenants/{tenant_id}/kunddata")
async def hamta_kunddata(request: Request, tenant_id: str) -> dict:
    """Registerraden med härledda värden pålagda, plus kontaktpersonerna."""
    tenant = await _hamta_tenant(request, tenant_id)
    storage = request.app.state.storage

    detaljer = await storage.get_customer_details(tenant_id) or {}
    falt: dict[str, dict] = {}
    for namn in KUNDDATA_FALT:
        varde = detaljer.get(namn)
        falt[namn] = {"varde": varde, "kalla": "manuell" if varde is not None else None}

    if falt["orgnr"]["varde"] is None:
        harledd = await _harledd_orgnr(storage, tenant_id)
        if harledd:
            falt["orgnr"] = {"varde": harledd, "kalla": "onboarding"}

    if falt["kund_sedan"]["varde"] is None and tenant.get("created_at"):
        skapad = tenant["created_at"]
        falt["kund_sedan"] = {
            "varde": skapad.date() if hasattr(skapad, "date") else skapad,
            "kalla": "system",
        }

    return {
        "kunddata": {
            "tenant": {
                "id": str(tenant["id"]),
                "slug": tenant.get("slug"),
                "name": tenant.get("name"),
            },
            "falt": falt,
            "kontakter": await storage.list_customer_contacts(tenant_id),
            "uppdaterad": detaljer.get("updated_at"),
        }
    }


@router.put("/tenants/{tenant_id}/kunddata")
async def spara_kunddata(
    request: Request, tenant_id: str, payload: KunddataRequest
) -> dict:
    """Sparar de fält som skickats med. None rör inte, tom sträng nollställer."""
    await _hamta_tenant(request, tenant_id)
    storage = request.app.state.storage

    falt = {namn: varde for namn, varde in payload.model_dump().items() if varde is not None}
    if not falt:
        return {"sparat": []}

    try:
        rad = await storage.upsert_customer_details(tenant_id, falt)
    except ValueError as fel:
        # normalisera_kunddata fäller t.ex. ett datum som inte parsar. 422 med
        # fältnamnet i texten — inte 500 ur en asyncpg-typkonvertering.
        raise HTTPException(status_code=422, detail=str(fel)) from fel

    await storage.log_platform_event(
        level="info",
        source="admin.kunddata",
        message=f"Kunduppgifter ändrade: {', '.join(sorted(falt))}.",
        tenant_id=tenant_id,
        detail={"falt": sorted(falt)},
    )
    return {"sparat": sorted(falt), "detaljer": rad}


@router.post("/tenants/{tenant_id}/kontakter")
async def skapa_kontakt(
    request: Request, tenant_id: str, payload: KontaktRequest
) -> dict:
    await _hamta_tenant(request, tenant_id)
    storage = request.app.state.storage

    if not (payload.namn or "").strip():
        raise HTTPException(status_code=422, detail="Kontaktpersonen behöver ett namn.")

    kontakt = await storage.create_customer_contact(
        tenant_id,
        namn=payload.namn,
        roll=payload.roll,
        mejl=payload.mejl,
        telefon=payload.telefon,
    )
    await storage.log_platform_event(
        level="info",
        source="admin.kunddata",
        message="Kontaktperson tillagd.",
        tenant_id=tenant_id,
        detail={"kontakt_id": str(kontakt["id"])},
    )
    return {"kontakt": kontakt}


@router.put("/tenants/{tenant_id}/kontakter/{contact_id}")
async def uppdatera_kontakt(
    request: Request, tenant_id: str, contact_id: str, payload: KontaktRequest
) -> dict:
    await _hamta_tenant(request, tenant_id)
    kraev_uuid(contact_id, "Kontaktpersonen")
    storage = request.app.state.storage

    kontakt = await storage.update_customer_contact(
        tenant_id,
        contact_id,
        namn=payload.namn,
        roll=payload.roll,
        mejl=payload.mejl,
        telefon=payload.telefon,
    )
    if not kontakt:
        raise HTTPException(status_code=404, detail="Kontaktpersonen finns inte.")

    await storage.log_platform_event(
        level="info",
        source="admin.kunddata",
        message="Kontaktperson uppdaterad.",
        tenant_id=tenant_id,
        detail={"kontakt_id": contact_id},
    )
    return {"kontakt": kontakt}


@router.delete("/tenants/{tenant_id}/kontakter/{contact_id}")
async def ta_bort_kontakt(request: Request, tenant_id: str, contact_id: str) -> dict:
    await _hamta_tenant(request, tenant_id)
    kraev_uuid(contact_id, "Kontaktpersonen")
    storage = request.app.state.storage

    if not await storage.delete_customer_contact(tenant_id, contact_id):
        raise HTTPException(status_code=404, detail="Kontaktpersonen finns inte.")

    await storage.log_platform_event(
        level="info",
        source="admin.kunddata",
        message="Kontaktperson borttagen.",
        tenant_id=tenant_id,
        detail={"kontakt_id": contact_id},
    )
    return {"borttagen": True}
