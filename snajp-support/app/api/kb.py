"""Tenant-specifik kunskapsbas: varje kundföretag läser och fyller sin egen.

Embeddings beräknas vid inläggning om en riktig OpenAI-nyckel finns; annars
lämnas kolumnen tom och sökningen faller tillbaka på fulltext/nyckelord.
"""

from fastapi import APIRouter, Depends, Request

from ..config import get_settings
from .deps import require_tenant
from .schemas import KbArticleRequest

router = APIRouter()


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
    # `embeddings` sägs ut, den antas inte. Artiklarna sparas även när vektorn
    # inte gick att räkna ut (se agent/embeddings.py), och skillnaden syns
    # annars först som att sökningen blivit sämre utan att något felat.
    return {"created": created, "embeddings": vektorer, "utan_vektor": len(created) - vektorer}
