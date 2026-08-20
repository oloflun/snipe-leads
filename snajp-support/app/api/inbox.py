"""Inkorgs-API: seedning/synk/ingest, lista, detalj och ta över — tenant-skopat."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from ..email_pipeline.connectors.mock import build_mock_emails
from ..email_pipeline.ingest import ingest_email
from ..email_pipeline.models import InboundAttachment, InboundEmail
from ..email_pipeline.poller import sync_imap_once
from ..email_pipeline.processor import process_email
from ..scripts.seed_kb import ensure_tenant_kb
from .deps import require_tenant
from .schemas import IngestEmailRequest

router = APIRouter()


@router.post("/api/inbox/mock", status_code=201)
async def seed_mock_inbox(
    request: Request,
    tenant: dict = Depends(require_tenant),
    x_snajp_demo: str | None = Header(default=None),
) -> dict:
    """Byter UT testmailen mot ett nytt urval och processar dem direkt.

    Tre saker skiljer sig från den första versionen, alla tre uppmätta mot
    dev-deployen 2026-08-19:

    1. **Tidigare testmail rensas.** Endpointen lade förut till samma sex mail
       igen, med nya id:n. Knappen heter "Hämta testmail" och gav en längre
       lista med samma innehåll — inte en ny.

    2. **Urvalet roterar.** `build_mock_emails()` väljer ur en pool och blandar
       besvarbara ärenden med sådana som ska eskalera. Se den modulen.

    3. **Kunskapsbasen säkerställs först — men BARA för en testarbetsyta.**
       Utan artiklar tvingar grundningsregeln eskalering av VARJE ärende
       (`processor.py` steg 2), och skärmen blir sex röda rader.

       Seedningen var först ogrindad, och det var ett fel av samma slag som
       delade tenants: `KB_ARTICLES` är Nordlys Handels e-handelsartiklar. En
       RIKTIG kund som tryckte på knappen fick alltså ett annat bolags
       returpolicy inlagd i sin egen grundningskälla, och grundningsgrinden ser
       en träff — den kan inte se att artikeln kom från fel företag.

       Grinden är `X-Snajp-Demo`, som proxyn sätter ur `workspaces.is_demo`
       (se `proxyWithApiKey` i app/api/snajp-support/_lib.ts) och som en klient
       inte kan sätta själv. En riktig kund får testmailen och behåller sin egen
       bas; att den är tom svarar endpointen om i `kb_tom`, så att UI:t kan säga
       det i stället för att kunden läser sex röda rader som ett produktfel.

    Ärendena (`ss_tickets`) och beslutsloggen rensas INTE. Inkorgen är en vy,
    loggen är spåret — ett ärende som fanns har funnits, och att radera spåret
    för att städa en demo är att göra granskningskedjan opålitlig.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]

    borttagna = await storage.delete_emails_by_provider(tenant_id, "mock")

    ar_testarbetsyta = (x_snajp_demo or "").lower() == "true"
    seedade_artiklar = await ensure_tenant_kb(storage, tenant_id) if ar_testarbetsyta else 0
    kb_tom = not await storage.list_kb(tenant_id)

    results = []
    for inbound in build_mock_emails():
        email = await ingest_email(storage, tenant_id, inbound)
        if email:
            outcome = await process_email(storage, tenant_id, email)
            results.append({"email_id": email["id"], **outcome})
    return {
        "ingested": len(results),
        "removed": borttagna,
        "kb_seeded": seedade_artiklar,
        "kb_tom": kb_tom,
        "results": results,
    }


@router.post("/api/inbox/sync")
async def sync_inbox(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Hämtar nya mail från konfigurerad IMAP-inkorg (Gmail/Outlook) nu."""
    return await sync_imap_once(request.app.state.storage, tenant["tenant_id"])


@router.post("/api/inbox/ingest", status_code=201)
async def ingest_external(
    request: Request, payload: IngestEmailRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """API-first-ingest: externa system postar inkommande mail hit."""
    storage = request.app.state.storage
    inbound = InboundEmail(
        provider="api",
        provider_message_id=payload.provider_message_id or f"api-{uuid.uuid4().hex}",
        from_email=payload.from_email,
        from_name=payload.from_name,
        subject=payload.subject,
        body_text=payload.body,
        attachments=[
            InboundAttachment(
                filename=a.filename,
                content_type=a.content_type,
                data_url=a.data_url,
                is_image=a.content_type.startswith("image/")
                or bool(a.data_url and a.data_url.startswith("data:image/")),
                size_bytes=len(a.data_url or ""),
            )
            for a in payload.attachments[:5]
        ],
    )
    email = await ingest_email(storage, tenant["tenant_id"], inbound)
    if email is None:
        raise HTTPException(status_code=409, detail="Mailet är redan mottaget (dublett).")
    outcome = await process_email(storage, tenant["tenant_id"], email)
    return {"email_id": email["id"], **outcome}


@router.get("/api/inbox")
async def list_inbox(
    request: Request,
    tenant: dict = Depends(require_tenant),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    emails = await request.app.state.storage.list_emails(
        tenant["tenant_id"], status=status, category=category, search=q, limit=limit
    )
    counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for email in emails:
        if email.get("classification"):
            key = email["classification"]["category"]
            counts[key] = counts.get(key, 0) + 1
        status_counts[email["status"]] = status_counts.get(email["status"], 0) + 1
    return {"emails": emails, "category_counts": counts, "status_counts": status_counts}


@router.get("/api/inbox/{email_id}")
async def get_email(
    request: Request, email_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    email = await request.app.state.storage.get_email(tenant["tenant_id"], email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Mailet finns inte.")
    return email


@router.post("/api/inbox/{email_id}/takeover")
async def takeover(
    request: Request, email_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Mänsklig handläggare tar över ärendet manuellt."""
    storage = request.app.state.storage
    email = await storage.get_email(tenant["tenant_id"], email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Mailet finns inte.")
    if email.get("draft") and email["draft"]["status"] == "pending":
        await storage.update_draft(tenant["tenant_id"], email["draft"]["id"], status="rejected")
        await storage.add_review(
            tenant["tenant_id"], draft_id=email["draft"]["id"], action="takeover"
        )
    await storage.update_email(tenant["tenant_id"], email_id, status="taken_over")
    await storage.log_decision(
        tenant["tenant_id"], email_id=email_id, event="taken_over",
        detail={"by": "human", "note": "Manuellt övertaget i dashboarden."},
    )
    return {"status": "taken_over"}
