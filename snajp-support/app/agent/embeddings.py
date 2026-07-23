"""Embeddings via OpenAI (endast riktig nyckel)."""

from openai import AsyncOpenAI

from ..config import get_settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    return _client


async def embed_text(text: str) -> list[float] | None:
    settings = get_settings()
    if settings.is_simulation():
        return None
    response = await _get_client().embeddings.create(
        model=settings.embedding_model, input=text[:8000]
    )
    return response.data[0].embedding
