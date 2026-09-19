"""Överlämnade chattar: medarbetarens sida av den sömlösa överlämningen.

Tenant-skopat (require_tenant). Portalens Chattar-vy (support-webb) når
routerna via sin generiska proxy /api/ag/* — samma nyckel och samma
exponering som resten av tenantytan. Se app/agent/overlamning.py för flödet.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..agent import overlamning, support_regler
from ..agent.support_agent import ar_overlamnat
from ..kanaler import KanalFel
from ..kanaler import leverans as kanaler_leverans
from .deps import kraev_uuid, require_tenant
from .schemas import MedarbetarsvarRequest

router = APIRouter()


def _med_orsakstext(rad: dict) -> dict:
    orsak = rad.get("overlamnad_orsak")
    return {
        **rad,
        "orsak_text": support_regler.ORSAKER.get(orsak or "", None),
        # Ett överlämnat samtal som legat stilla längre än giltighetstiden
        # besvaras av agenten igen — vyn ska kunna säga det i stället för att
        # visa det som om kunden fortfarande väntade.
        "aktiv": ar_overlamnat(rad),
    }


@router.get("/api/chattar")
async def lista_chattar(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    rader = await request.app.state.storage.list_chat_handovers(tenant["tenant_id"], limit=100)
    return {"chattar": [_med_orsakstext(r) for r in rader]}


@router.get("/api/chattar/{customer_id}")
async def hamta_chatt(
    request: Request, customer_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(customer_id, "Kunden")
    storage = request.app.state.storage
    meddelanden = await overlamning.samtalsutskrift(storage, tenant["tenant_id"], customer_id)
    if not meddelanden:
        raise HTTPException(status_code=404, detail="Samtalet finns inte.")
    samtal = await storage.get_chat_state(tenant["tenant_id"], customer_id)
    return {"samtal": _med_orsakstext(samtal), "meddelanden": meddelanden}


@router.post("/api/chattar/{customer_id}/svar", status_code=201)
async def svara_i_chatt(
    request: Request,
    customer_id: str,
    payload: MedarbetarsvarRequest,
    tenant: dict = Depends(require_tenant),
) -> dict:
    kraev_uuid(customer_id, "Kunden")
    try:
        resultat = await overlamning.medarbetarsvar(
            request.app.state.storage, tenant["tenant_id"], customer_id, payload.text
        )
    except overlamning.OverlamningsFel as fel:
        raise HTTPException(status_code=409, detail=str(fel)) from None
    # Kanalerna (bd snipe-36u): en kund i WhatsApp, Messenger, Slack eller
    # Teams har ingen widget som hämtar svaret — det måste SKICKAS dit. Svaret
    # är redan sparat; ett leveransfel (t.ex. WhatsApps 24-timmarsfönster)
    # redovisas för medarbetaren i stället för att fälla anropet.
    levererat: bool | None = None
    leveransfel: str | None = None
    try:
        levererat = await kanaler_leverans.leverera(
            request.app.state.storage,
            tenant["tenant_id"],
            customer_id=customer_id,
            kanal=resultat["ticket"].get("channel"),
            text=payload.text,
        ) or None
    except KanalFel as fel:
        levererat, leveransfel = False, str(fel)
    return {
        "message": resultat["message"],
        "ticket_id": resultat["ticket"]["id"],
        # None = webbchatten (hämtar själv), True = skickat i kanalen,
        # False = sparat men inte levererat (se leveransfel).
        "levererat": levererat,
        "leveransfel": leveransfel,
    }


@router.post("/api/chattar/{customer_id}/aterlamna")
async def aterlamna_chatt(
    request: Request, customer_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(customer_id, "Kunden")
    samtal = await overlamning.aterlamna(request.app.state.storage, tenant["tenant_id"], customer_id)
    return {"samtal": _med_orsakstext(samtal)}
