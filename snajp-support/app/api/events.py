"""Plattformshändelser — det som gick fel, sparat i stället för utskrivet.

Före migration 026 fanns inga FastAPI-exception-handlers alls och ingen
middleware. Ohanterade fel gick till stdout på Render, där de rullar förbi
och försvinner vid nästa spin-down. Tre ställen i leads-koden svalde dessutom
fel utan spår. "Det funkar inte för kunden" gick alltså bara att felsöka
genom att be kunden göra om det medan någon tittade på loggen.

Loggningen får ALDRIG kasta vidare. Ett fel i felloggningen som fäller
requesten förvandlar en hanterbar bugg till ett avbrott, och gör dessutom
grundorsaken osynlig bakom sig själv.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any

logger = logging.getLogger("snajp-support.events")

LEVELS = ("error", "warning", "info")


async def log_event(
    storage,
    *,
    level: str,
    source: str,
    message: str,
    tenant_id: str | None = None,
    run_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Skriver en rad till platform_events. Sväljer sina egna fel."""
    if level not in LEVELS:
        level = "error"
    try:
        await storage.log_platform_event(
            level=level,
            source=source,
            message=message[:2000],
            tenant_id=tenant_id,
            run_id=run_id,
            detail=detail or {},
        )
    except Exception:  # noqa: BLE001 — se modulens docstring
        logger.warning("platform_events: kunde inte skriva %s/%s", source, message[:80])


async def log_exception(
    storage,
    error: BaseException,
    *,
    source: str,
    tenant_id: str | None = None,
    run_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Som log_event, med traceback i detail.

    Tracebacken kapas: den är till för att peka ut raden, inte för att vara
    en andra kopia av koden i databasen.
    """
    detail = dict(extra or {})
    detail["traceback"] = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )[-4000:]
    detail["exception_type"] = type(error).__name__
    await log_event(
        storage,
        level="error",
        source=source,
        message=f"{type(error).__name__}: {error}",
        tenant_id=tenant_id,
        run_id=run_id,
        detail=detail,
    )


def install_exception_handler(app) -> None:
    """Fångar allt som ingen route hanterade.

    Registreras på Exception, inte på HTTPException: en 404 eller en 422 är
    ett svar, inte ett fel, och att logga dem hade dränkt notiscentret i
    normal trafik.
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, error: Exception):  # noqa: ANN202
        storage = getattr(request.app.state, "storage", None)
        if storage is not None:
            await log_exception(
                storage,
                error,
                source="api",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    # Ingen query, ingen body: de kan innehålla kunddata, och
                    # ett notiscenter är inte rätt ställe att lagra den.
                },
            )
        logger.exception("Ohanterat fel på %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "Något gick fel på vår sida. Felet är loggat."},
        )
