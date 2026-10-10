"""Mätning per anrop: hur många databasfrågor och hur lång tid i databasen.

Svarar i `Server-Timing` (webbläsarens nätverkspanel visar den, och webbens
proxy skickar den vidare) och loggar anrop som tar längre än
`MATNING_LOGG_MS`. Byggd 2026-10-10 när varje proxat anrop tog 100–200 ms i
api:t utan att något pekade ut var.

Frågorna räknas med asyncpg:s query logger, som anropas via `call_soon` i
anroparens kontext — räknaren är därför ett muterbart objekt i en
ContextVar, inte ett värde som skrivs om. En fråga vars logg hinner köras
först efter att svarshuvudet skickats räknas inte; det gäller i praktiken
bara bakgrundsjobb, som inte mäts här.
"""

from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger("snajp-support.matning")

_matare: ContextVar[dict[str, float] | None] = ContextVar("snajp_matning", default=None)


def logga_fraga(record: Any) -> None:
    """asyncpg query logger: lägger frågans tid på det pågående anropet."""
    m = _matare.get()
    if m is not None:
        m["n"] += 1
        m["db"] += float(getattr(record, "elapsed", 0.0) or 0.0)


class Matning:
    """Rent ASGI-mellanlager (inget BaseHTTPMiddleware: det kostar en task per anrop)."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.logg_ms = int(os.environ.get("MATNING_LOGG_MS", "400"))

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        m = {"n": 0, "db": 0.0}
        token = _matare.set(m)
        start = time.perf_counter()

        async def skicka(message: dict) -> None:
            if message["type"] == "http.response.start":
                total = (time.perf_counter() - start) * 1000
                db = m["db"] * 1000
                huvuden = list(message.get("headers", []))
                huvuden.append(
                    (
                        b"server-timing",
                        f'db;dur={db:.1f};desc="{int(m["n"])} q", app;dur={max(total - db, 0):.1f}'.encode(),
                    )
                )
                message = {**message, "headers": huvuden}
                if self.logg_ms > 0 and total >= self.logg_ms:
                    logger.warning(
                        "Långsamt anrop: %s %s %.0f ms (%d frågor, %.0f ms i databasen)",
                        scope.get("method"), scope.get("path"), total, m["n"], db,
                    )
            await send(message)

        try:
            await self.app(scope, receive, skicka)
        finally:
            _matare.reset(token)
