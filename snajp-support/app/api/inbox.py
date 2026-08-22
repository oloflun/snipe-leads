"""Inkorgs-API: seedning/synk/ingest, lista, detalj och ta över — tenant-skopat."""

import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request

from ..email_pipeline.connectors.mock import build_mock_emails
from ..email_pipeline.ingest import ingest_email
from ..email_pipeline.models import InboundAttachment, InboundEmail
from ..email_pipeline.poller import (
    host_for_mailbox,
    password_env_name,
    sync_imap_once,
    sync_mailbox,
)
from ..email_pipeline.processor import process_email
from ..config import CATEGORIES, get_settings
from ..scripts.seed_kb import ensure_tenant_kb
from .deps import require_tenant
from .schemas import IngestEmailRequest, SeedMockRequest

logger = logging.getLogger("snajp-support.inbox")

router = APIRouter()


@router.post("/api/inbox/mock", status_code=201)
async def seed_mock_inbox(
    request: Request,
    bakgrund: BackgroundTasks,
    payload: SeedMockRequest | None = None,
    tenant: dict = Depends(require_tenant),
    x_snajp_demo: str | None = Header(default=None),
) -> dict:
    """Lägger nya testmail i inkorgen och svarar DIREKT.

    ## Varför den inte längre väntar på agenten

    Endpointen processade förut alla sex mailen genom hela pipelinen innan den
    svarade. Uppmätt mot dev-deployen 2026-08-22: **60,3 sekunder**. Proxyn i
    webbappen har `maxDuration = 60`, så anropet hann dödas innan svaret kom —
    knappen "Hämta testmail" snurrade för alltid, och kunden såg en produkt som
    hängt sig. Det var felrapporten.

    Nu: mailen skrivs in och svaret går tillbaka på en gång. Klassificering och
    utkast görs i en bakgrundsuppgift, och inkorgen visar ärendena med en gång
    medan de fylls på. Att se agenten arbeta är dessutom en bättre demo än att
    se en spinner i en minut.

    ## Vad `category` gör

    Utan fack byts HELA testinkorgen ut. Med fack byts bara det facket —
    det är vad "Uppdatera" gör när kunden står i ett filtrerat läge. Utan den
    möjligheten fyllde varje klick hela inkorgen igen och det fack man tittade
    på råkade få noll nya mail.

    ## Kunskapsbasen säkerställs först — men BARA för en testarbetsyta

    Utan artiklar tvingar grundningsregeln eskalering av VARJE ärende
    (`processor.py` steg 2), och skärmen blir sex röda rader.

    Seedningen var först ogrindad, och det var ett fel av samma slag som delade
    tenants: `KB_ARTICLES` är Nordlys Handels e-handelsartiklar. En RIKTIG kund
    som tryckte på knappen fick alltså ett annat bolags returpolicy inlagd i sin
    egen grundningskälla, och grundningsgrinden ser en träff — den kan inte se
    att artikeln kom från fel företag.

    Grinden är `X-Snajp-Demo`, som proxyn sätter ur `workspaces.is_demo` (se
    `proxyWithApiKey` i app/api/snajp-support/_lib.ts) och som en klient inte kan
    sätta själv.

    Ärendena (`ss_tickets`) och beslutsloggen rensas INTE. Inkorgen är en vy,
    loggen är spåret — ett ärende som fanns har funnits, och att radera spåret
    för att städa en demo är att göra granskningskedjan opålitlig.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]

    kategori = (payload.category if payload else None) or None
    if kategori and kategori not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Okänt fack: {kategori}")
    antal = max(1, min((payload.antal if payload else None) or 8, 10))

    borttagna = await storage.delete_mock_emails(tenant_id, category=kategori)

    ar_testarbetsyta = (x_snajp_demo or "").lower() == "true"
    seedade_artiklar = await ensure_tenant_kb(storage, tenant_id) if ar_testarbetsyta else 0
    kb_tom = not await storage.list_kb(tenant_id)

    inlasta = []
    for inbound in build_mock_emails(antal=antal, kategori=kategori):
        email = await ingest_email(storage, tenant_id, inbound)
        if email:
            inlasta.append(email)

    # Processningen sker EFTER svaret. Se docstringen: det är hela skillnaden
    # mellan en knapp som svarar och en som ser ut att ha hängt sig.
    bakgrund.add_task(_processa_i_bakgrunden, storage, tenant_id, inlasta)

    return {
        "ingested": len(inlasta),
        "removed": borttagna,
        "kb_seeded": seedade_artiklar,
        "kb_tom": kb_tom,
        "category": kategori,
        # Ärendena finns i inkorgen redan nu, men utan klassificering och
        # utkast. UI:t använder flaggan för att fortsätta läsa om listan tills
        # agenten är klar i stället för att visa en tom kolumn som ett fel.
        "processing": bool(inlasta),
        "email_ids": [e["id"] for e in inlasta],
    }


async def _processa_i_bakgrunden(storage, tenant_id: str, mail: list[dict]) -> None:
    """Klassificerar och skriver utkast för nyss inlästa mail.

    Fångar per mail: ett fel på ett ärende (LLM-timeout, en bild som inte går
    att läsa) ska inte lämna de fem andra oprocessade. Ingen returväg finns —
    resultatet syns i inkorgen, och det som misslyckades ligger kvar som `new`.
    """
    for email in mail:
        try:
            await process_email(storage, tenant_id, email)
        except Exception:  # noqa: BLE001 — ett trasigt ärende stoppar inte de andra
            logger.exception("Bakgrundsprocessning misslyckades för mail %s", email.get("id"))


async def _tenant_slug(storage, tenant_id: str) -> str:
    """Slugen för lösenordsnyckeln IMAP_PASSWORD_<SLUG>.

    Står inte i `require_tenant`, som bara bär id och namn. Att härleda slugen
    ur namnet vore en gissning ("Livrustnings AB" -> ?), och fel gissning ger
    fel miljövariabel och en synk som tyst hittar noll mail.
    """
    tenant = await storage.get_tenant(tenant_id)
    return (tenant or {}).get("slug") or ""


@router.get("/api/inbox/mailboxes")
async def list_inbox_mailboxes(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Vilka inkorgar den här kunden har kopplade, och om de går att synka.

    Finns för att UI:t inte ska behöva GISSA. "Synka inkorg" satt förut som en
    alltid synlig knapp som för varje kund utan kopplad inkorg svarade "IMAP är
    inte konfigurerat (IMAP_HOST/USER/PASSWORD)" — en felutskrift som namnger
    miljövariabler kunden varken kan se eller sätta. En knapp som alltid
    misslyckas är värre än ingen knapp: den lär kunden att produkten är trasig.

    Svaret bär ALDRIG ett lösenord. Adressen och värden räcker för att svara på
    frågan "är något kopplat", och lösenordet bor i env under
    IMAP_PASSWORD_<SLUG> just för att en läsbehörighet på ss_mailboxes inte ska
    räcka för att läsa kundens mail (se poller.py).
    """
    storage = request.app.state.storage
    settings = get_settings()

    inkorgar = [
        m
        for m in await storage.list_mailboxes(tenant["tenant_id"])
        if m.get("provider") != "mock"
    ]

    slug = await _tenant_slug(storage, tenant["tenant_id"])
    har_losenord = bool(slug and os.environ.get(password_env_name(slug)))

    # Den globala envvägen räknas som en kopplad inkorg. Den finns kvar för
    # enkelinstallationer och för testerna.
    global_konfigurerad = bool(
        settings.imap_host and settings.imap_user and settings.imap_password
    )

    rader = [
        {
            "address": m.get("address"),
            "provider": m.get("provider"),
            "status": m.get("status"),
            "host": host_for_mailbox(m),
            "last_sync_at": m.get("last_sync_at"),
            "last_error": m.get("last_error"),
            # Utan lösenord kan raden inte synkas. Det sägs rakt ut, så att
            # UI:t kan skilja "ingen inkorg" från "inkorg utan nyckel".
            "kan_synka": bool(host_for_mailbox(m)) and har_losenord,
        }
        for m in inkorgar
    ]

    return {
        "mailboxes": rader,
        "global_konfigurerad": global_konfigurerad,
        "kan_synka": global_konfigurerad or any(r["kan_synka"] for r in rader),
    }


@router.post("/api/inbox/sync")
async def sync_inbox(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Hämtar nya mail från KUNDENS egna inkorgar nu.

    Routen synkade förut alltid mot de GLOBALA IMAP-inställningarna
    (IMAP_HOST/USER/PASSWORD) oavsett vilken tenant som frågade. Två fel i ett:

    1. **Fel inkorg.** I en flerkundsinstallation pekar de globala värdena på
       en enda brevlåda. Var den satt hade varje kunds synk hämtat samma mail —
       alltså en annan kunds post in i den här kundens ärenden. Att den inte var
       satt är hela skälet till att det aldrig hände.
    2. **Fel besked.** Var den inte satt svarade routen med namnen på tre
       miljövariabler. Kunden läser ett konfigurationsfel i sitt eget UI, för
       något bara vi kan åtgärda.

    Nu: kundens rader i `ss_mailboxes` synkas, en i taget, med samma väg som
    den periodiska pollern använder. Den globala envvägen är kvar som fallback
    för enkelinstallationer och för testerna, och används bara när kunden inte
    har någon egen inkorgsrad.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]

    inkorgar = [
        m
        for m in await storage.list_mailboxes(tenant_id)
        if m.get("status") == "active" and m.get("provider") != "mock"
    ]

    if not inkorgar:
        settings = get_settings()
        if settings.imap_host and settings.imap_user and settings.imap_password:
            return {"connected": True, **await sync_imap_once(storage, tenant_id)}
        return {
            "fetched": 0,
            "processed": 0,
            "connected": False,
            "error": "Ingen inkorg är kopplad ännu. Vi kopplar er Gmail eller Outlook åt er.",
        }

    slug = await _tenant_slug(storage, tenant_id)
    hamtade = 0
    processade = 0
    fel: list[str] = []
    for mailbox in inkorgar:
        summering = await sync_mailbox(storage, tenant_id, slug, mailbox)
        hamtade += summering.get("fetched", 0)
        processade += summering.get("processed", 0)
        if summering.get("error"):
            fel.append(str(summering["error"]))

    return {
        "fetched": hamtade,
        "processed": processade,
        "connected": True,
        "error": " ".join(fel) or None,
    }


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
