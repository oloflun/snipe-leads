"""Samma start två gånger ger EN start (Fas 0-fyndet H5, 2026-11-09).

"Kör Iris", "Skriv utkast" och "Godkänn och skicka alla" hade ingen spärr mot
ett andra klick. Knappen är avstängd medan sidan väntar, men det räcker inte:
webbens proxy ger en POST nio sekunder, visar sedan ett fel fast backenden
arbetar vidare, och användaren klickar igen. Två körningar startade, eller
samma utkast köades två gånger.

`en_gang` låter den första begäran göra arbetet. En likadan begäran från samma
kund som kommer medan den första pågår, eller inom fönstret efteråt, får samma
svar tillbaka (märkt `dubblett`) i stället för att starta något nytt. Faller
den första får den andra samma fel.

Per process, med flit: api:t är en process (Dockerfile). Körs fler repliker
behöver nyckeln ligga i Redis, som körningslåsen (se DEPLOY.md).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

#: Hur länge en likadan begäran räknas som samma klick. Längre än proxyns
#: nio sekunder plus användarens reaktionstid; kortare än att någon hinner
#: vilja starta en likadan körning med flit.
FONSTER_S = 30.0

_poster: dict[str, tuple[float, asyncio.Future]] = {}


def nyckel(tenant_id: str, handling: str, innehall: Any = None) -> str:
    """Kund + handling + begärans innehåll. Olika innehåll är olika starter."""
    ra = json.dumps(innehall, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{tenant_id}|{handling}|{ra}".encode("utf-8")).hexdigest()


def _stada(nu: float, fonster_s: float) -> None:
    for k, (tid, framtid) in list(_poster.items()):
        # >=: med fonster_s=0 ("bara medan arbetet pågår") ska en klar post
        # städas även när klockan inte hunnit ticka sedan den blev klar.
        if framtid.done() and nu - tid >= fonster_s:
            _poster.pop(k, None)


async def en_gang(
    nyckelvarde: str,
    arbete: Callable[[], Awaitable[dict]],
    *,
    fonster_s: float = FONSTER_S,
) -> dict:
    nu = time.monotonic()
    _stada(nu, fonster_s)
    befintlig = _poster.get(nyckelvarde)
    if befintlig is not None:
        # shield: att den ANDRA begäran avbryts (klienten gav upp) får inte
        # avbryta den förstas arbete.
        svar = await asyncio.shield(befintlig[1])
        return {**svar, "dubblett": True}

    framtid: asyncio.Future = asyncio.get_running_loop().create_future()
    _poster[nyckelvarde] = (nu, framtid)
    try:
        svar = await arbete()
    except BaseException as fel:
        # Ett misslyckat försök ska gå att göra om direkt.
        _poster.pop(nyckelvarde, None)
        if not framtid.done():
            framtid.set_exception(fel)
            framtid.exception()  # hämtat: ingen "never retrieved"-varning utan väntare
        raise
    framtid.set_result(svar)
    _poster[nyckelvarde] = (time.monotonic(), framtid)
    return svar


def nollstall() -> None:
    """För testerna."""
    _poster.clear()
