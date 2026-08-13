"""Tenant-specifik kunskapsbas: varje kundföretag läser och fyller sin egen.

Embeddings beräknas vid inläggning om en riktig LLM-nyckel finns; annars
lämnas kolumnen tom och sökningen faller tillbaka på fulltext/nyckelord.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import CATEGORIES, CATEGORY_HINTS, CATEGORY_LABELS, get_settings
from ..kb_templates import PLACEHOLDER_PREFIX, as_articles
from .deps import require_tenant
from .schemas import KbArticleRequest, KbArticleUpdate

router = APIRouter()


@router.get("/api/categories")
async def get_categories(tenant: dict = Depends(require_tenant)) -> dict:
    """Facken med etikett och förklaring — så UI:t slipper duplicera listan."""
    return {
        "categories": [
            {"id": c, "label": CATEGORY_LABELS[c], "hint": CATEGORY_HINTS.get(c, "")}
            for c in CATEGORIES
        ]
    }


@router.get("/api/kb")
async def list_kb(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    articles = await request.app.state.storage.list_kb(tenant["tenant_id"])
    for article in articles:
        article["is_placeholder"] = article.get("content", "").startswith(PLACEHOLDER_PREFIX)
    return {
        "tenant_name": tenant["tenant_name"],
        "articles": articles,
        "placeholder_count": sum(1 for a in articles if a["is_placeholder"]),
    }


async def _embed(article_title: str, content: str):
    if get_settings().is_simulation():
        return None
    from ..agent.embeddings import embed_text

    return await embed_text(f"{article_title}\n{content}")


@router.post("/api/kb", status_code=201)
async def add_kb_articles(
    request: Request, payload: KbArticleRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    created = []
    for article in payload.articles:
        created.append(
            await storage.add_kb_article(
                tenant["tenant_id"],
                title=article.title,
                content=article.content,
                category=article.category,
                embedding=await _embed(article.title, article.content),
            )
        )
    return {"created": created}


@router.put("/api/kb/{article_id}")
async def update_kb_article(
    request: Request,
    article_id: str,
    payload: KbArticleUpdate,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Redigera en egen artikel. En annan tenants artikel finns helt enkelt inte."""
    if payload.category and payload.category not in CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Okänt fack: {payload.category}")

    storage = request.app.state.storage
    # Embedding räknas om bara när texten faktiskt ändrats — annars pekar
    # vektorn på den gamla lydelsen och sökträffarna blir fel.
    embedding = None
    if payload.title is not None or payload.content is not None:
        existing = next(
            (a for a in await storage.list_kb(tenant["tenant_id"]) if a["id"] == article_id),
            None,
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Artikeln finns inte.")
        embedding = await _embed(
            payload.title or existing["title"], payload.content or existing["content"]
        )

    updated = await storage.update_kb_article(
        tenant["tenant_id"],
        article_id,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        embedding=embedding,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Artikeln finns inte.")
    return updated


@router.delete("/api/kb/{article_id}")
async def delete_kb_article(
    request: Request, article_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    deleted = await request.app.state.storage.delete_kb_article(
        tenant["tenant_id"], article_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Artikeln finns inte.")
    return {"deleted": True, "id": article_id}


@router.post("/api/kb/template", status_code=201)
async def seed_template(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Fyller arbetsytan med branschmallen som tydligt märkta platshållare.

    Ger en ny pilotkund rätt STRUKTUR direkt — rubriker och kategorier som styr
    sökträffarna — medan innehållet ska ersättas med bolagets egna villkor.
    Hoppar över artiklar vars rubrik redan finns, så den kan köras om.
    """
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    existing = {a["title"] for a in await storage.list_kb(tenant_id)}

    created = []
    for article in as_articles(prefixed=True):
        if article["title"] in existing:
            continue
        created.append(
            await storage.add_kb_article(
                tenant_id,
                title=article["title"],
                content=article["content"],
                category=article["category"],
                embedding=await _embed(article["title"], article["content"]),
            )
        )
    return {
        "created": len(created),
        "skipped": len(as_articles()) - len(created),
        "note": (
            "Artiklarna är märkta [PLATSHÅLLARE]. Ersätt texten med era egna "
            "villkor innan piloten går skarpt."
        ),
    }
