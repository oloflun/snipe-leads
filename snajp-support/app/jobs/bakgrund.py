"""Arbete som tar längre än en begäran, med förlopp där användaren startade det.

## Varför

Webbens proxy ger en POST nio sekunder. Kvittoskanningen och "Godkänn och
skicka alla" gör sitt arbete inne i begäran och tar ofta längre: vyn visade
ett fel medan arbetet gick vidare på servern, utan förlopp och utan utfall
efter en omladdning (fas 0-fyndet H4). Projektregeln säger motsatsen: allt som
tar mer än ett ögonblick ska visa förlopp och utfall där det startades.

## Hur

`starta` skapar en jobbpost (samma lager som chattens och leadsjobbens, Redis
i drift) och kör arbetet i en bakgrundsuppgift i processen. Arbetet får ett
`Forlopp` att skriva till; vyn hämtar posten med `lasa` och ser status,
förlopp och till sist resultatet.

Ingen ny kö: uppgiften lever i api-processen. Dör processen mitt i (en
deploy) stannar arbetet där, och jobbposten fälls av jobblagrets tidsgräns så
att vyn får ett besked. Det som hunnit göras är gjort; arbetet som läggs här
ska därför gå att starta om utan att något händer två gånger (skanningen
hoppar över lästa mejl, utskicken över skickade utkast).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger("snajp-support.bakgrund")

#: Det användaren läser när arbetet föll av ett skäl vi inte har en text för.
#: Felet i sig står i loggen.
ALLMANT_FEL = "Det gick inte att slutföra. Försök igen om en stund."

#: Starka referenser: en uppgift utan ägare kan städas bort mitt i arbetet.
_uppgifter: set[asyncio.Task] = set()
#: Pågående arbete per nyckel (kund + slag), så att en andra start medan det
#: första går får samma jobb i stället för ett till.
_pagaende: dict[str, str] = {}


class Forlopp:
    """Skriver förloppet på jobbposten. Kastar aldrig: förloppet är en
    upplysning och får inte fälla arbetet."""

    def __init__(self, jobs: Any, job_id: str) -> None:
        self._jobs = jobs
        self.job_id = job_id

    async def satt(self, **falt: Any) -> None:
        try:
            # `started` flyttar jobblagrets tidsgräns: arbete som rapporterar
            # lever, hur länge det än tar sammanlagt.
            await self._jobs.annotate(self.job_id, forlopp=falt, started=time.time())
        except Exception:  # noqa: BLE001
            logger.warning("Kunde inte skriva förloppet för jobb %s.", self.job_id)


def _feltext(fel: BaseException) -> str:
    if isinstance(fel, HTTPException) and isinstance(fel.detail, str) and fel.detail:
        return fel.detail
    return ALLMANT_FEL


async def starta(
    app_state: Any,
    tenant_id: str,
    slag: str,
    arbete: Callable[[Forlopp], Awaitable[dict[str, Any]]],
) -> tuple[str, bool]:
    """Startar arbetet och svarar med (job_id, pagar). `pagar` är sant när
    samma slags arbete redan går för kunden: då startas inget nytt."""
    nyckel = f"{tenant_id}:{slag}"
    befintligt = _pagaende.get(nyckel)
    if befintligt:
        post = await app_state.jobs.get(befintligt)
        if post and post.get("status") not in ("completed", "failed"):
            return befintligt, True
        _pagaende.pop(nyckel, None)

    job_id = await app_state.jobs.create(tenant_id=tenant_id)
    _pagaende[nyckel] = job_id
    forlopp = Forlopp(app_state.jobs, job_id)

    async def _kor() -> None:
        try:
            resultat = await arbete(forlopp)
            await app_state.jobs.complete(job_id, resultat)
        except Exception as fel:  # noqa: BLE001 — jobbet får aldrig bli stående utan besked
            if not isinstance(fel, HTTPException):
                logger.exception("Bakgrundsarbetet %s föll (jobb %s, kund %s)", slag, job_id, tenant_id)
            try:
                await app_state.jobs.fail(job_id, _feltext(fel))
            except Exception:  # noqa: BLE001
                logger.exception("Kunde inte skriva felet på jobb %s", job_id)
        finally:
            if _pagaende.get(nyckel) == job_id:
                _pagaende.pop(nyckel, None)

    uppgift = asyncio.create_task(_kor())
    _uppgifter.add(uppgift)
    uppgift.add_done_callback(_uppgifter.discard)
    return job_id, False


async def lasa(app_state: Any, tenant_id: str, job_id: str) -> dict[str, Any]:
    """Jobbets läge för kundens vy. 404 om jobbet inte finns hos kunden."""
    post = await app_state.jobs.get(job_id)
    if not post or post.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=404, detail="Jobbet finns inte eller har städats bort.")
    return {
        "status": post["status"],
        "forlopp": post.get("forlopp"),
        "result": post.get("result"),
        "error": post.get("error"),
    }


def nollstall() -> None:
    """Bara för tester."""
    _pagaende.clear()
