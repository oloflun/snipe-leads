"""Granskningsflödet: godkänn (ev. redigerat), avvisa — med human_reviews-spår.

Vid godkännande skickas svaret på riktigt via SMTP. Ärendet markeras som
skickat ENDAST om leveransen lyckades — annars ligger utkastet kvar som
pending och felet returneras, så att ingen tror att kunden fått svar.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from ..email_pipeline.sender import send_reply
from .deps import require_tenant
from .schemas import ApproveDraftRequest, RejectDraftRequest

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
    if draft["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Utkastet är redan {draft['status']}.")

    email = await storage.get_email(tenant_id, draft["email_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Mailet finns inte.")

    edited = payload.edited_content is not None and payload.edited_content != draft["content"]
    content = payload.edited_content if edited else draft["content"]

    settings = get_settings()
    delivered = False
    delivery_note = ""

    if payload.send is False:
        # Explicit "godkänn utan att skicka" — texten hanteras manuellt.
        delivery_note = "Godkänt utan utskick (hanteras manuellt)."
    elif not settings.can_send_email():
        raise HTTPException(
            status_code=503,
            detail=(
                "SMTP är inte konfigurerat, så svaret kan inte skickas. Sätt "
                "SMTP-/IMAP-uppgifterna, eller godkänn med send=false för att "
                "hantera utskicket manuellt."
            ),
        )
    else:
        ok, result = await send_reply(
            to_email=email["from_email"],
            subject=email["subject"] or "Ditt ärende",
            body=content,
            in_reply_to=email.get("provider_message_id"),
        )
        if not ok:
            await storage.log_decision(
                tenant_id,
                email_id=draft["email_id"],
                event="send_failed",
                detail={"error": result},
            )
            raise HTTPException(status_code=502, detail=result)
        delivered = True
        delivery_note = f"Skickat till {email['from_email']} ({result})."

    # Först när leveransen är klar (eller medvetet hoppad) uppdateras tillståndet.
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

    await storage.update_email(
        tenant_id, draft["email_id"], status="sent" if delivered else "approved"
    )
    await storage.log_decision(
        tenant_id,
        email_id=draft["email_id"],
        event="approved_and_sent" if delivered else "approved_no_send",
        detail={"edited": edited, "note": delivery_note},
    )
    return {
        "status": "sent" if delivered else "approved",
        "delivered": delivered,
        "edited": edited,
        "content": content,
        "note": delivery_note,
    }


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
    if draft["status"] != "pending":
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
