"""Embeddingcache (Fas R2, INV-CACHE-001) — sparar vektorn för en text som
redan embeddats, så samma fråga aldrig kostar två embedding-anrop.

Husets paritetsmönster: ett `Protocol` med två implementationer bakom samma
kontrakt, plus modul-nivå `konfigurera`/`hamta_cache` (samma stil som
`app/jobs/store.py`s Memory/Redis-par och `app/agent/llm.py`s modulstate).
Utan Redis konfigurerad används `MinnesEmbeddingCache` — den sparar ändå
upprepade anrop INOM samma process (KB-sökningen och svarscachen embeddar
ofta samma fråga två gånger i en och samma körning), och gör testerna
deterministiska utan nätverk.

Kroken sitter i `app/agent/embeddings.embed_text`: slå upp FÖRE det riktiga
anropet, spara EFTER. Ingenting annat i kodbasen ska anropa Gemini för en
embedding utan att gå den vägen.
"""

from __future__ import annotations

import hashlib
import logging
import struct
import time
from ..redisnycklar import nyckel
from typing import Any, Protocol

logger = logging.getLogger("snajp-support.cache.embedding")

#: 30 dagar. En embedding är en ren funktion av texten — den blir aldrig
#: "fel" av att åldras, TTL:en finns bara för att hålla databasen liten
#: (gratis-30MB:n i R5-planen) och för att en text som aldrig återkommer inte
#: ska ligga kvar för evigt.
TTL_SEKUNDER = 30 * 24 * 60 * 60


class EmbeddingCache(Protocol):
    async def get(self, text: str) -> list[float] | None: ...
    async def set(self, text: str, vektor: list[float]) -> None: ...


def _nyckel(text: str) -> str:
    return nyckel("embcache:" + hashlib.sha256((text or "").encode("utf-8")).hexdigest())


class MinnesEmbeddingCache:
    """Process-lokal dict med TTL-städning. Ingen Redis krävs — det är
    defaulten, och testerna kör mot den här."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, list[float]]] = {}

    async def get(self, text: str) -> list[float] | None:
        self._stada()
        post = self._store.get(_nyckel(text))
        return list(post[1]) if post else None

    async def set(self, text: str, vektor: list[float]) -> None:
        self._store[_nyckel(text)] = (time.time() + TTL_SEKUNDER, list(vektor))

    def _stada(self) -> None:
        # Städas vid LÄSNING, inte med en bakgrundstask — samma resonemang
        # som MemoryJobStore._sweep: en process-lokal cache behöver ingen
        # egen klocka, bara att inte svara med utgången data.
        nu = time.time()
        doda = [k for k, (utgar, _) in self._store.items() if utgar < nu]
        for k in doda:
            del self._store[k]


class RedisEmbeddingCache:
    """Redis-backad. Värdet är BINÄRPACKADE float32 via `struct`, inte JSON:
    1536 tal blir ~6 KB binärt mot ~30 KB som JSON-array (varje flyttal som
    text, med kommatecken och hakparenteser runt) — fem gånger mindre i en
    databas där R5-planens första nivå är 250 MB totalt.
    """

    def __init__(self, client: Any) -> None:
        self._redis = client
        self._loggat_fel = False

    async def get(self, text: str) -> list[float] | None:
        try:
            raw = await self._redis.get(_nyckel(text))
        except Exception:  # noqa: BLE001 — se _logga_fel
            self._logga_fel("läsning")
            return None
        if not raw:
            return None
        try:
            antal = len(raw) // 4
            return list(struct.unpack(f"{antal}f", raw))
        except struct.error:
            # Skadad/ofullständig post — behandla som cache-miss, inte fel.
            return None

    async def set(self, text: str, vektor: list[float]) -> None:
        try:
            packad = struct.pack(f"{len(vektor)}f", *vektor)
            await self._redis.set(_nyckel(text), packad, ex=TTL_SEKUNDER)
        except Exception:  # noqa: BLE001 — en cache som inte går att skriva får inte fälla anropet
            self._logga_fel("skrivning")

    def _logga_fel(self, vad: str) -> None:
        # EN gång per process, samma resonemang som agent/embeddings.py:
        # en cache-miss om och om igen (varje KB-sökning, varje ärende) hade
        # dränkt loggen med samma rad.
        if not self._loggat_fel:
            self._loggat_fel = True
            logger.warning(
                "Embeddingcache-%s mot Redis misslyckades — fortsätter utan cache "
                "(embeddings räknas om varje gång, men inget anrop faller).",
                vad,
            )


_cache: EmbeddingCache = MinnesEmbeddingCache()


def konfigurera(redis_client: Any | None = None) -> None:
    """Växlar backend. `None` (defaulten) => en FÄRSK `MinnesEmbeddingCache`
    — inte bara "ingen Redis", utan en tömd cache. Testerna anropar den här
    med `None` mellan körningar för att isolera anropsräkningen; utan det
    hade den andra testfilen sett cacheposter den första lämnat kvar."""
    global _cache
    _cache = RedisEmbeddingCache(redis_client) if redis_client is not None else MinnesEmbeddingCache()


def hamta_cache() -> EmbeddingCache:
    return _cache
