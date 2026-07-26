"""Embeddings via OpenAI. DeepSeek saknar embeddings — kräver separat OpenAI-nyckel.

Utan giltig embeddings-klient returneras None och storage-lagret faller tillbaka
på svensk full-text-sökning i kunskapsbasen.
"""

from ..config import get_settings
from .llm import get_embedding_client


async def embed_text(text: str) -> list[float] | None:
    client = get_embedding_client()
    if client is None:
        return None
    settings = get_settings()
    response = await client.embeddings.create(model=settings.embedding_model, input=text[:8000])
    return response.data[0].embedding
