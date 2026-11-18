"""Tenant-specifik kunskapsbas: varje kundföretag läser och fyller sin egen.

Embeddings beräknas vid inläggning om en riktig OpenAI-nyckel finns; annars
lämnas kolumnen tom och sökningen faller tillbaka på fulltext/nyckelord.
"""

import asyncio
import base64
import logging
import re
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from . import rate_limit_db
from .deps import require_tenant
from .schemas import KbArticleRequest, KbExtraheraRequest, KbForslagBeslutRequest, KbSkannaRequest

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
                source_url=article.source_url,
                giltig_till=article.giltig_till,
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


#: En skanning som står som pågående längre än så räknas som avbruten (en
#: omstart av api-tjänsten mitt i), och en ny får starta.
SKANNING_HANGER_MINUTER = 30


#: Småord som inte skiljer två rubriker åt.
_SMAORD = frozenset({"och", "för", "av", "på", "i", "om", "med", "till", "en", "ett", "the", "of", "and", "for"})


def titelnyckel(titel: str) -> str:
    """Rubriken som en jämförelsenyckel. Två utkast med samma nyckel är samma
    artikel för kunden.

    Skiftläge, skiljetecken, småord och ordföljd räknas inte, och ett
    genitiv-s tas bort, så att "Priser för Snajp-tjänster" och "Priser för
    Snajps tjänster" blir samma. Uppmätt i development 2026-11-18: skanningen
    av snajp.se gav båda som egna förslag.
    """
    ord_ = re.findall(r"[0-9a-zåäöéü]+", (titel or "").casefold())
    rensade = {o[:-1] if len(o) > 4 and o.endswith("s") else o for o in ord_ if o not in _SMAORD}
    return " ".join(sorted(rensade))


def nya_forslag(utkast: list[dict], befintliga_titlar: Iterable[str]) -> tuple[list[dict], int]:
    """Utkasten som kompletterar kunskapsbasen, och antalet som redan fanns.

    Ett utkast hoppas över när kunden redan har en artikel med samma rubrik,
    när det föreslagits förut (även avvisat), eller när samma skanning gav det
    två gånger. Kundens egna artiklar ändras aldrig härifrån: förslagen blir
    nya artiklar, och bara när kunden lägger till dem.
    """
    sedda = {titelnyckel(t) for t in befintliga_titlar}
    sedda.discard("")
    nya: list[dict] = []
    for artikel in utkast:
        nyckel = titelnyckel(artikel.get("title", ""))
        if not nyckel or nyckel in sedda or not (artikel.get("content") or "").strip():
            continue
        sedda.add(nyckel)
        nya.append(artikel)
    return nya, len(utkast) - len(nya)


async def _spara_utfall(storage, tenant_id: str, skanning_id: str, resultat: dict) -> None:
    """Sparar skanningens utkast som förslag, utan dubbletter, och avslutar raden."""
    befintliga = [a.get("title", "") for a in await storage.list_kb(tenant_id)]
    befintliga += [f.get("title", "") for f in await storage.list_kb_forslag(tenant_id)]
    nya, redan_fanns = nya_forslag(resultat.get("artiklar") or [], befintliga)
    await storage.add_kb_forslag(tenant_id, skanning_id, nya)
    await storage.avsluta_kb_skanning(
        tenant_id,
        skanning_id,
        status="klar",
        sidor=resultat.get("sidor"),
        lasbara_sidor=resultat.get("lasbara_sidor"),
        forslag=len(nya),
        redan_fanns=redan_fanns,
    )


async def _kor_skanning(
    app_state,
    job_id: str,
    webbplats: str,
    bolagsnamn: str,
    scopes,
    *,
    tenant_id: str | None = None,
    skanning_id: str | None = None,
) -> None:
    from .. import kb_skanning

    storage = app_state.storage
    try:
        await app_state.jobs.start(job_id)
        resultat = await kb_skanning.skanna(webbplats, bolagsnamn, kb_skanning.bygg_anropare())
        # Modellanropen räknas mot tenantens vanliga LLM-tak, som allt annat.
        await rate_limit_db.record(app_state.storage, scopes, resultat["anrop"])
        if resultat["anrop"] and len(resultat["fel"]) == resultat["anrop"]:
            if skanning_id:
                await storage.avsluta_kb_skanning(
                    tenant_id, skanning_id, status="fel", sidor=resultat.get("sidor"),
                    lasbara_sidor=resultat.get("lasbara_sidor"),
                    fel="Sidorna lästes, men utkasten gick inte att skriva. Försök igen om en stund.",
                )
            await app_state.jobs.fail(job_id, resultat["fel"][0])
            return
        if skanning_id:
            await _spara_utfall(storage, tenant_id, skanning_id, resultat)
        await app_state.jobs.complete(job_id, resultat)
    except Exception as fel:  # noqa: BLE001 — jobbet ska alltid landa i ett slutläge
        logger.exception("kb-skanning föll för %s", webbplats)
        if skanning_id:
            try:
                await storage.avsluta_kb_skanning(
                    tenant_id, skanning_id, status="fel", fel="Skanningen avbröts. Försök igen om en stund."
                )
            except Exception:  # noqa: BLE001 — raden får inte fälla jobbets slutläge
                logger.exception("kb-skanningens rad kunde inte avslutas")
        await app_state.jobs.fail(job_id, f"Skanningen avbröts ({type(fel).__name__}).")


async def _pagaende_skanning(storage, tenant_id: str) -> dict | None:
    """Den pågående skanningen, om den inte har hängt sig."""
    senaste = await storage.senaste_kb_skanning(tenant_id)
    if not senaste or senaste.get("status") != "pagar":
        return None
    try:
        startad = datetime.fromisoformat(str(senaste["startad_at"]))
    except (KeyError, ValueError):
        return None
    if startad.tzinfo is None:
        startad = startad.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - startad > timedelta(minutes=SKANNING_HANGER_MINUTER):
        await storage.avsluta_kb_skanning(
            tenant_id, senaste["id"], status="fel", fel="Skanningen avbröts. Försök igen."
        )
        return None
    return senaste


@router.post("/api/kb/skanna", status_code=202)
async def skanna_webbplats(
    request: Request, payload: KbSkannaRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Skannar kundens EGEN webbplats till artikelutkast (app/kb_skanning.py).

    Svarar 202 med ett jobb-id; resultatet pollas via GET /api/jobs/{id}.
    Kunskapsbasen rörs aldrig. Med `spara` blir utkasten förslag som kunden
    lägger till eller avvisar (GET /api/kb/forslag), och skanningens läge
    sparas så att den går att följa efter en omladdning. Onboardingen startar
    den så. Utan `spara` finns utkasten bara i jobbsvaret.
    """
    from ..leads.discovery import normalisera_webbplats, webbplats_ar_bolagets

    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]

    async def neka(detalj: str, adress: str) -> HTTPException:
        # En sparad skanning som inte kunde starta syns ändå för kunden, med
        # skälet, i stället för att onboardingen tyst inte gav något.
        if payload.spara:
            await storage.skapa_kb_skanning(
                tenant_id, webbplats=adress, startad_av=payload.startad_av, status="fel", fel=detalj
            )
        return HTTPException(status_code=422, detail=detalj)

    try:
        webbplats = normalisera_webbplats(payload.webbplats.strip())
    except Exception as fel:  # noqa: BLE001 — en adress som inte går att tolka
        raise await neka("Adressen går inte att läsa.", payload.webbplats.strip()) from fel
    if not webbplats_ar_bolagets(webbplats):
        raise await neka(
            "Ange er egen webbplats. Register, annonsplattformar och exempeldomäner skannas inte.", webbplats
        )
    from .. import kb_skanning

    if not await asyncio.to_thread(kb_skanning.ar_publik_vard, webbplats):
        raise await neka("Webbplatsen hittades inte.", webbplats)

    if payload.spara:
        # En skanning i taget. Startas den igen medan en pågår (onboardingen
        # skickas om, kunden trycker två gånger) svarar vi med den som pågår.
        pagar = await _pagaende_skanning(storage, tenant_id)
        if pagar:
            return {"job_id": None, "status": "pagar", "webbplats": pagar["webbplats"], "skanning": pagar}
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

    skanning = None
    if payload.spara:
        skanning = await storage.skapa_kb_skanning(
            tenant_id, webbplats=webbplats, startad_av=payload.startad_av
        )
    job_id = await request.app.state.jobs.create(tenant_id=tenant_id, status="queued")
    uppgift = asyncio.create_task(
        _kor_skanning(
            request.app.state,
            job_id,
            webbplats,
            tenant.get("tenant_name") or "",
            scopes,
            tenant_id=tenant_id,
            skanning_id=skanning["id"] if skanning else None,
        )
    )
    _pagaende.add(uppgift)
    uppgift.add_done_callback(_pagaende.discard)
    return {"job_id": job_id, "status": "queued", "webbplats": webbplats, "skanning": skanning}


@router.get("/api/kb/forslag")
async def kb_forslag(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Senaste skanningen och de utkast som väntar på kundens beslut."""
    storage = request.app.state.storage
    skanning = await _pagaende_skanning(storage, tenant["tenant_id"]) or await storage.senaste_kb_skanning(
        tenant["tenant_id"]
    )
    forslag = await storage.list_kb_forslag(tenant["tenant_id"], status="vantar")
    return {"skanning": skanning, "forslag": forslag}


@router.post("/api/kb/forslag/beslut")
async def besluta_kb_forslag(
    request: Request, payload: KbForslagBeslutRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Lägger till eller avvisar utkast. Ett tillagt utkast blir en NY artikel,
    med samma väg som en handskriven (inbäddning, KB-versionen bumpas). En
    befintlig artikel ändras aldrig: finns rubriken redan i basen när kunden
    trycker, hoppas utkastet över och räknas som `fanns_redan`."""
    settings = get_settings()
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    tillagda: list[str] = []
    avvisade: list[str] = []
    fanns_redan: list[str] = []
    titlar = {titelnyckel(a.get("title", "")) for a in await storage.list_kb(tenant_id)}

    for forslag_id in dict.fromkeys(payload.ids):
        if payload.beslut == "avvisa":
            if await storage.besluta_kb_forslag(tenant_id, forslag_id, status="avvisad"):
                avvisade.append(forslag_id)
            continue
        forslag = await storage.besluta_kb_forslag(tenant_id, forslag_id, status="tillagd")
        if not forslag:
            continue
        nyckel = titelnyckel(forslag["title"])
        if nyckel in titlar:
            # Kunden har redan en artikel med den rubriken. Den rörs inte;
            # utkastet lämnar listan som avvisat.
            await storage.angra_kb_forslag(tenant_id, forslag_id)
            await storage.besluta_kb_forslag(tenant_id, forslag_id, status="avvisad")
            fanns_redan.append(forslag_id)
            continue
        try:
            embedding = None
            if not settings.is_simulation():
                from ..agent.embeddings import embed_text

                embedding = await embed_text(f"{forslag['title']}\n{forslag['content']}")
            artikel = await storage.add_kb_article(
                tenant_id,
                title=forslag["title"],
                content=forslag["content"],
                category=forslag["category"],
                embedding=embedding,
                source_url=forslag.get("source_url"),
            )
        except Exception:
            # Artikeln sparades inte: utkastet ska stå kvar som väntande, inte
            # se tillagt ut.
            await storage.angra_kb_forslag(tenant_id, forslag_id)
            raise
        await storage.satt_kb_forslag_artikel(tenant_id, forslag_id, artikel["id"])
        titlar.add(nyckel)
        tillagda.append(forslag_id)

    if tillagda:
        from ..cache import versioner

        await versioner.bumpa_kb(tenant_id)
    return {"tillagda": tillagda, "avvisade": avvisade, "fanns_redan": fanns_redan}


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
