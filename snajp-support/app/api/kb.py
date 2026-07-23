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
    for article in payload.articles:
        embedding = None
        if not settings.is_simulation():
            from ..agent.embeddings import embed_text

            embedding = await embed_text(f"{article.title}\n{article.content}")
        created.append(
            await storage.add_kb_article(
                tenant["tenant_id"],
                title=article.title,
                content=article.content,
                category=article.category,
                embedding=embedding,
            )
        )
    return {"created": created}
