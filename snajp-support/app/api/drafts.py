"""Granskningsflödet: godkänn (ev. redigerat), avvisa — med human_reviews-spår."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..budget import SupportBudgetExceededError, kontrollera_support_budget
from ..email_pipeline.omformulering import omformulera_utkast
from ..email_pipeline.sender import SandningsFel, skicka_supportsvar
from .deps import require_tenant
from .schemas import ApproveDraftRequest, OmformuleraDraftRequest, RejectDraftRequest

router = APIRouter()


@router.post("/api/drafts/{draft_id}/approve")
async def approve_draft(
    request: Request,
    draft_id: str,
    payload: ApproveDraftRequest,
    tenant: dict = Depends(require_tenant),
) -> dict:
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    draft = await storage.get_draft(tenant_id, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Utkastet finns inte.")
    if draft["status"] not in ("pending",):
        raise HTTPException(status_code=409, detail=f"Utkastet är redan {draft['status']}.")

    edited = payload.edited_content is not None and payload.edited_content != draft["content"]
    content = payload.edited_content if edited else draft["content"]

    # Sändningen sker FÖRE varje statusskrivning. Ordningen är kontraktet:
    # misslyckas den riktiga sändningen (SandningsFel) står utkastet kvar som
    # pending och kunden ser ett 502 — aldrig ett "skickat" på ett mejl som
    # inte gick ut. Fram till 2026-08-28 fanns ingen sändning alls här, och
    # statusen sattes ändå; se email_pipeline/sender.py för hela resonemanget.
    email = await storage.get_email(tenant_id, draft["email_id"])
    try:
        import inspect
        if "tenant_id" in inspect.signature(skicka_supportsvar).parameters:
            sandnotering = await skicka_supportsvar(email, content=content, tenant_id=tenant_id, storage=storage)
        else:
            sandnotering = await skicka_supportsvar(email, content=content)
    except SandningsFel as fel:
        raise HTTPException(status_code=502, detail=str(fel)) from fel

    await storage.update_draft(tenant_id, draft_id, status="approved", content=content)
    await storage.add_review(
        tenant_id,
        draft_id=draft_id,
        action="edit" if edited else "approve",
        edited_content=payload.edited_content if edited else None,
        note=payload.note,
    )
    if draft.get("ticket_id"):
        ticket = await storage.get_ticket(tenant_id, draft["ticket_id"])
        if ticket and ticket.get("conversation_id"):
            await storage.save_message(
                tenant_id,
                conversation_id=ticket["conversation_id"],
                direction="outbound",
                content=content,
            )
        await storage.update_ticket(tenant_id, draft["ticket_id"], status="resolved")
    await storage.update_email(tenant_id, draft["email_id"], status="sent")
    await storage.log_decision(
        tenant_id,
        email_id=draft["email_id"],
        event="approved_and_sent",
        detail={
            "edited": edited,
            # Noteringen kommer från sender.py och säger SANNINGEN för just
            # det här mejlet: skickat via SMTP, simulerat, eller testmejl.
            "note": sandnotering,
        },
    )
    return {"status": "sent", "edited": edited, "content": content}


@router.post("/api/drafts/{draft_id}/omformulera")
async def omformulera_draft(
    request: Request,
    draft_id: str,
    payload: OmformuleraDraftRequest,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Skriver om utkastet i vald riktning och returnerar den nya texten.

    Persisterar INGENTING: utkastet står kvar som pending med sitt original,
    och den omskrivna texten blir verklig först när granskaren godkänner den
    (approve med edited_content). Se omformulering.py för hela resonemanget.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    draft = await storage.get_draft(tenant_id, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Utkastet finns inte.")
    if draft["status"] not in ("pending",):
        raise HTTPException(status_code=409, detail=f"Utkastet är redan {draft['status']}.")

    # Samma dygnsbudget som resten av supporten: en omformulering är ett
    # LLM-anrop och ska inte kunna köras obegränsat när taket är nått.
    try:
        await kontrollera_support_budget(storage, tenant_id)
    except SupportBudgetExceededError as fel:
        raise HTTPException(status_code=429, detail=str(fel)) from fel

    email = await storage.get_email(tenant_id, draft["email_id"])
    text = payload.content if (payload.content or "").strip() else draft["content"]
    nytt = await omformulera_utkast(lage=payload.lage, content=text, email=email)

    await storage.log_decision(
        tenant_id,
        email_id=draft["email_id"],
        event="draft_omformulerad",
        detail={"lage": payload.lage},
    )
    return {"content": nytt, "lage": payload.lage}


@router.post("/api/drafts/{draft_id}/reject")
async def reject_draft(
    request: Request,
    draft_id: str,
    payload: RejectDraftRequest,
    tenant: dict = Depends(require_tenant),
) -> dict:
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    draft = await storage.get_draft(tenant_id, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Utkastet finns inte.")
    if draft["status"] not in ("pending",):
        raise HTTPException(status_code=409, detail=f"Utkastet är redan {draft['status']}.")

    await storage.update_draft(tenant_id, draft_id, status="rejected")
    await storage.add_review(
        tenant_id, draft_id=draft_id, action="reject", note=payload.note
    )
    await storage.update_email(tenant_id, draft["email_id"], status="rejected")
    await storage.log_decision(
        tenant_id,
        email_id=draft["email_id"],
        event="draft_rejected",
        detail={"note": payload.note or ""},
    )
    return {"status": "rejected"}
