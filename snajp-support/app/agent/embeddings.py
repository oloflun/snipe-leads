"""Embeddings via Gemini. DeepSeek saknar embeddings — kräver separat nyckel.

Utan giltig embeddings-klient returneras None och storage-lagret faller tillbaka
på svensk full-text-sökning i kunskapsbasen.

## Varför ett misslyckat ANROP behandlas som en saknad klient

Modulen lovade degradering men levererade den bara i ett av två fall: `client is
None` gav None, medan en klient som fanns men fick 403 kastade rakt igenom.

Det inträffade skarpt 2026-08-21. GEMINI_API_KEY var satt i båda Railway-
miljöerna, alltså fanns en klient — men Gemini-API:t var aldrig aktiverat på
Google-projektet, så varje anrop svarade 403. Följden var att `POST /api/kb`
och `POST /api/inbox/mock` svarade 500: det gick inte att lägga till en enda
artikel i någon kunskapsbas, och det gick inte att generera ett testmejl.
`/health/ready` sa `mode: live` utan invändning, eftersom den mäter LLM-nyckeln
och inte embeddings.

En kunskapsbasartikel är text. Att vägra spara texten för att vektorn inte gick
att räkna ut är att låta en försämring bli ett avbrott — sökningen har en
fungerande väg utan vektorn, och det är den `search_kb` faller tillbaka på.

Felet loggas EN gång per process. Ett fel per artikel hade dränkt loggen vid en
seedning av tjugotvå artiklar, och det är samma fel varje gång.
"""

import logging

from ..cache.embeddingcache import hamta_cache
from ..config import get_settings
from .llm import get_embedding_client

logger = logging.getLogger(__name__)

_har_klagat = False


async def embed_text(text: str) -> list[float] | None:
    """Embeddar `text`, via embeddingcachen (Fas R2, `app/cache/
    embeddingcache.py`) om samma text redan embeddats. Kroken gäller VARJE
    anropare — KB-sökningen (`_sok_kb` i support_agent.py) OCH den
    semantiska svarscachen (`app/cache/svarscache.forbered`) delar alltså
    samma cache, utan att någon av dem behöver veta om den."""
    global _har_klagat

    cache = hamta_cache()
    cachad = await cache.get(text)
    if cachad is not None:
        return cachad

    client = get_embedding_client()
    if client is None:
        return None
    settings = get_settings()
    try:
        if settings.google_service_account_json:
            # Vertex egna inbäddnings-API (:predict). Den OpenAI-kompatibla
            # vägen hos Vertex svarar 500 på varje inbäddningsanrop sedan
            # 2026-09-12, uppmätt igen 2026-10-06, och kunskapsbasen söktes
            # därför bara med fulltext i alla miljöer.
            vektor = await _vertex_predict(settings, text[:8000])
        else:
            response = await client.embeddings.create(
                model=settings.embedding_model,
                input=text[:8000],
                # Måste begäras. Utan `dimensions` ger gemini-embedding-001 3072
                # värden, och kolumnen är vector(1536) — se config.py.
                dimensions=settings.embedding_dimensions,
            )
            vektor = response.data[0].embedding
    except Exception as fel:  # noqa: BLE001 — se docstringen
        if not _har_klagat:
            _har_klagat = True
            logger.error(
                "Embeddings otillgängliga (%s: %s). Kunskapsbasen sparas utan vektorer "
                "och söks med svensk full-text tills det är löst.",
                type(fel).__name__,
                str(fel)[:300],
            )
        return None
    await cache.set(text, vektor)
    return vektor


async def _vertex_predict(settings, text: str) -> list[float]:
    """En vektor via Vertex :predict, i samma region som språkmodellen (EU)."""
    import json

    import httpx

    from .llm import _vertex_token

    projekt = json.loads(settings.google_service_account_json)["project_id"]
    region = settings.google_cloud_region
    url = (
        f"https://{region}-aiplatform.googleapis.com/v1/projects/{projekt}/locations/{region}"
        f"/publishers/google/models/{settings.embedding_model}:predict"
    )
    async with httpx.AsyncClient(timeout=30.0) as klient:
        svar = await klient.post(
            url,
            headers={"Authorization": f"Bearer {_vertex_token(settings)}"},
            json={
                "instances": [{"content": text}],
                "parameters": {"outputDimensionality": settings.embedding_dimensions},
            },
        )
    svar.raise_for_status()
    return svar.json()["predictions"][0]["embeddings"]["values"]


def embeddings_tillgangliga() -> bool:
    """Falskt om klienten saknas eller ett anrop redan har misslyckats.

    Läses av POST /api/kb för att kunna SÄGA att artiklarna sparades utan
    vektorer. En tyst försämring är den sortens fel man upptäcker veckor senare
    som "sökningen hittar inte längre".
    """
    return get_embedding_client() is not None and not _har_klagat
