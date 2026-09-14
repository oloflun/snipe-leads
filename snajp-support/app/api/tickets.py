"""Inspektionsendpoints: ärenden och kundhistorik (tenant-skopade)."""

from fastapi import APIRouter, Depends, HTTPException, Request

from .deps import kraev_uuid, require_tenant

router = APIRouter()


@router.get("/api/tickets/{ticket_id}")
async def get_ticket(
    request: Request, ticket_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(ticket_id, "Ärendet")
    ticket = await request.app.state.storage.get_ticket(tenant["tenant_id"], ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ärendet finns inte.")
    return ticket


@router.get("/api/customers/{customer_id}/history")
async def get_customer_history(
    request: Request, customer_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(customer_id, "Kunden")
    tickets = await request.app.state.storage.get_customer_history(
        tenant["tenant_id"], customer_id
    )
    return {"customer_id": customer_id, "tickets": tickets}
