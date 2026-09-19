"""Tenant-specifik kunskapsbas: varje kundföretag läser och fyller sin egen.

Embeddings beräknas vid inläggning om en riktig OpenAI-nyckel finns; annars
lämnas kolumnen tom och sökningen faller tillbaka på fulltext/nyckelord.
"""

import asyncio
import base64
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from . import rate_limit_db
from .deps import require_tenant
from .schemas import KbArticleRequest, KbExtraheraRequest, KbSkannaRequest

router = APIRouter()
logger = logging.getLogger(__name__)

#: Skanningar per tenant och timme (rate_limit_db:s fönster). En skanning är
#: högst MAX_LLM_ANROP modellanrop plus tjugo sidhämtningar — taket är till för
#: en kund som trycker om och om igen, inte för normal användning.
SKANNINGAR_PER_TIMME = 5
SKANNING = "kb_skanning"

#: Referenser till pågående skanningar, så att skräpsamlaren inte tar en
#: uppgift som bara event-loopen håller i (asyncio.create_task är svag).
_pagaende: set[asyncio.Task] = set()

#: Taket är på de AVKODADE bytesen, ~8 MB enligt planen (Fas 5.5). Schemat
#: begränsar redan den råa strängen (base64-påslaget är ~4/3), det här är den
#: exakta kontrollen efter avkodning.
MAX_PDF_BYTES = 8 * 1024 * 1024

#: Under den här snittlängden per sida räknas textlagret som glest — typiskt
#: en skannad eller bildbaserad PDF där pypdf bara fångar enstaka artefakter
#: i stället för löptext. Talet är inte en exakt vetenskap, men en riktig
#: brödtext ligger på hundratals tecken per sida, en tom sida på noll.
GLEST_TROSKEL_TECKEN_PER_SIDA = 20


def _dekoda_data_url(data_url: str) -> tuple[str, bytes]:
    """`data:<mimetyp>;base64,<data>` till (mimetyp, bytes).

    Kastar ValueError på allt som inte har den formen, i stället för att
    krascha djupare i base64-avkodningen med ett meddelande ingen förstår.
    """
    if not data_url.startswith("data:") or "," not in data_url:
        raise ValueError("filen är inte en data-URL")
    header, _, encoded = data_url.partition(",")
    if ";base64" not in header:
        raise ValueError("data-URL:en saknar base64-kodning")
    mimetyp = header[len("data:") :].split(";", 1)[0] or "application/octet-stream"
    try:
        data = base64.b64decode(encoded, validate=True)
    except Exception as orsak:  # noqa: BLE001 — base64 kastar flera olika typer
        raise ValueError("filens innehåll gick inte att avkoda") from orsak
    return mimetyp, data


@router.get("/api/kb")
async def list_kb(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    articles = await request.app.state.storage.list_kb(tenant["tenant_id"])
    return {"tenant_name": tenant["tenant_name"], "articles": articles}


@router.post("/api/kb", status_code=201)
async def add_kb_articles(
    request: Request, payload: KbArticleRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    settings = get_settings()
    storage = request.app.state.storage
    created = []
    vektorer = 0
    for article in payload.articles:
        embedding = None
        if not settings.is_simulation():
            from ..agent.embeddings import embed_text

            embedding = await embed_text(f"{article.title}\n{article.content}")
        if embedding is not None:
            vektorer += 1
        created.append(
            await storage.add_kb_article(
                tenant["tenant_id"],
                title=article.title,
                content=article.content,
                category=article.category,
                embedding=embedding,
            )
        )
    if created:
        # Fas R2 (INV-CACHE-001): en ny/ändrad KB-artikel kan ändra svaret på
        # en fråga som redan har en cachad post. Bumpa KB-versionen så att
        # varenda gammal svarscachepost för den här tenanten blir omatchbar
        # — se app/cache/versioner.py.
        from ..cache import versioner

        await versioner.bumpa_kb(tenant["tenant_id"])

    # `embeddings` sägs ut, den antas inte. Artiklarna sparas även när vektorn
    # inte gick att räkna ut (se agent/embeddings.py), och skillnaden syns
    # annars först som att sökningen blivit sämre utan att något felat.
    return {"created": created, "embeddings": vektorer, "utan_vektor": len(created) - vektorer}


@router.delete("/api/kb/{artikel_id}")
async def ta_bort_kb_artikel(
    request: Request, artikel_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """En artikel som inte längre stämmer ska kunna tas bort — annars citerar
    agenten den för alltid. Samma KB-versionsbump som vid inläggning."""
    if not await request.app.state.storage.delete_kb_article(tenant["tenant_id"], artikel_id):
        raise HTTPException(status_code=404, detail="Artikeln finns inte.")
    from ..cache import versioner

    await versioner.bumpa_kb(tenant["tenant_id"])
    return {"deleted": artikel_id}


async def _kor_skanning(app_state, job_id: str, webbplats: str, bolagsnamn: str, scopes) -> None:
    from .. import kb_skanning

    try:
        await app_state.jobs.start(job_id)
        resultat = await kb_skanning.skanna(webbplats, bolagsnamn, kb_skanning.bygg_anropare())
        # Modellanropen räknas mot tenantens vanliga LLM-tak, som allt annat.
        await rate_limit_db.record(app_state.storage, scopes, resultat["anrop"])
        if resultat["anrop"] and len(resultat["fel"]) == resultat["anrop"]:
            await app_state.jobs.fail(job_id, resultat["fel"][0])
            return
        await app_state.jobs.complete(job_id, resultat)
    except Exception as fel:  # noqa: BLE001 — jobbet ska alltid landa i ett slutläge
        logger.exception("kb-skanning föll för %s", webbplats)
        await app_state.jobs.fail(job_id, f"Skanningen avbröts ({type(fel).__name__}).")


@router.post("/api/kb/skanna", status_code=202)
async def skanna_webbplats(
    request: Request, payload: KbSkannaRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Skannar kundens EGEN webbplats till artikelutkast (app/kb_skanning.py).

    Svarar 202 med ett jobb-id; resultatet pollas via GET /api/jobs/{id}.
    Ingenting sparas: utkasten visas, kunden väljer, och de valda går genom
    POST /api/kb precis som en handskriven artikel.
    """
    from ..leads.discovery import normalisera_webbplats, webbplats_ar_bolagets

    try:
        webbplats = normalisera_webbplats(payload.webbplats.strip())
    except Exception as fel:  # noqa: BLE001 — en adress som inte går att tolka
        raise HTTPException(status_code=422, detail="Adressen går inte att läsa.") from fel
    if not webbplats_ar_bolagets(webbplats):
        raise HTTPException(
            status_code=422,
            detail="Ange er egen webbplats — register, annonsplattformar och exempeldomäner skannas inte.",
        )
    from .. import kb_skanning

    if not await asyncio.to_thread(kb_skanning.ar_publik_vard, webbplats):
        raise HTTPException(status_code=422, detail="Webbplatsen hittades inte.")

    storage = request.app.state.storage
    skanningar = [rate_limit_db.Scope("tenant", tenant["tenant_id"], SKANNINGAR_PER_TIMME, SKANNING)]
    scopes = rate_limit_db.scopes_for(tenant["tenant_id"], request.headers.get("x-snajp-user"))
    try:
        await rate_limit_db.enforce(storage, skanningar + scopes)
    except rate_limit_db.RateLimitDbExceededError as fel:
        raise HTTPException(
            status_code=429, detail="För många skanningar den senaste timmen. Försök igen senare."
        ) from fel
    # Skanningen räknas när den STARTAR, så att fem snabba klick inte blir tio.
    await rate_limit_db.record(storage, skanningar, 1)

    job_id = await request.app.state.jobs.create(tenant_id=tenant["tenant_id"], status="queued")
    uppgift = asyncio.create_task(
        _kor_skanning(request.app.state, job_id, webbplats, tenant.get("tenant_name") or "", scopes)
    )
    _pagaende.add(uppgift)
    uppgift.add_done_callback(_pagaende.discard)
    return {"job_id": job_id, "status": "queued", "webbplats": webbplats}


@router.post("/api/kb/extrahera")
async def extrahera_pdf(
    payload: KbExtraheraRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """PDF till text, för en SYNLIG förhandsvisning innan något sparas.

    Kunskapsbasens egen invändning mot att göra om PDF (components/settings/
    Kunskapsbas.tsx: "en halvläst PDF ger tyst sönderhackad text som agenten
    sedan citerar som om den vore korrekt") gäller det TYSTA. Den invändningen
    besvaras inte genom att fortsätta låta bli, den besvaras genom att göra
    extraktionen SYNLIG: den här endpointen extraherar och returnerar texten
    plus en varning när textlagret ser tunt eller tomt ut, men skriver
    ingenting. Kunden läser förhandsvisningen och godkänner den, precis som
    den skrivna texten i textrutan, genom samma POST /api/kb som resten av
    kunskapsbasen redan använder. Ingenting skrivs härifrån, och filen sparas
    aldrig, bara textlagret som extraherades ur den.

    tenant-beroendet finns bara för att stänga ytan för oinloggad trafik —
    extraktionen är beräkning utan sidoeffekt och rör inte tenantens data.
    """
    try:
        mimetyp, data = _dekoda_data_url(payload.data_url)
    except ValueError as fel:
        raise HTTPException(status_code=422, detail=f"Ogiltig fil: {fel}") from fel

    if mimetyp != "application/pdf":
        raise HTTPException(
            status_code=422, detail=f"Bara PDF stöds här, filen är {mimetyp}."
        )
    if not data:
        raise HTTPException(status_code=422, detail="Filen är tom.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Filen är {len(data) // 1024 // 1024} MB, taket är "
                f"{MAX_PDF_BYTES // 1024 // 1024} MB."
            ),
        )

    import io

    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        sidor = len(reader.pages)
        text = "\n".join(sida.extract_text() or "" for sida in reader.pages).strip()
    except Exception as orsak:  # noqa: BLE001 — pypdf kastar flera olika typer
        raise HTTPException(
            status_code=422, detail=f"PDF:en gick inte att läsa: {orsak}"
        ) from orsak

    if sidor == 0:
        raise HTTPException(status_code=422, detail="PDF:en har inga sidor.")

    varning = None
    if not text:
        varning = (
            "Textlagret är tomt. Det här är troligen en skannad PDF utan "
            "maskinläsbar text. Klistra in texten för hand i stället."
        )
    elif len(text) / sidor < GLEST_TROSKEL_TECKEN_PER_SIDA:
        varning = (
            "Textlagret är mycket glest i förhållande till sidantalet. Läs "
            "igenom förhandsvisningen noga innan du lägger till den, det kan "
            "vara en delvis skannad eller bildbaserad PDF."
        )

    return {"text": text, "sidor": sidor, "varning": varning}
