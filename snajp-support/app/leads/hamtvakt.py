"""Hämtvakten: leadshämtarna når bara det publika nätet.

## Varför

Iris hämtar bolagens webbplatser från vår server. Adressen kommer ur
registret, ur en sökning eller från kunden själv (ett prospekt som läggs till
för hand), och en webbplats kan omdirigera vart som helst. Utan spärr går
hämtningen att peka mot molnets metadatatjänst (169.254.169.254), localhost
eller en intern Railway-adress, med svaret inläst i researchen och kanske
återgivet för kunden (Fas 0, 2026-11-09).

Kundens integrationer har spärren sedan tidigare
(app/integrationer/natvakt.py). Reglerna är desamma här, med en skillnad:
http tillåts. En integration är ett API och ska tala https; en liten firmas
webbplats gör det inte alltid, och den ska gå att läsa ändå.

## Hur

`krokar()` ges till httpx-klienten som `event_hooks`. Kroken körs före VARJE
förfrågan klienten skickar, alltså också före varje omdirigering den följer.
En spärrad adress blir ett `httpx.ConnectError`: hämtarna fångar redan
`httpx.HTTPError` och behandlar det som en sajt som inte svarar.

DNS-ombindning mellan kontrollen och anslutningen täcks inte, av samma skäl
som i nätvakten (se dess docstring).
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

import httpx

from ..integrationer import natvakt

logger = logging.getLogger("snajp-support.hamtvakt")


async def kontrollera(url: str) -> None:
    """Kastar natvakt.NatvaktError om adressen inte är en publik webbadress."""
    try:
        schema = urlsplit(url).scheme.lower()
    except ValueError as fel:
        raise natvakt.NatvaktError(f"Ogiltig adress: {url[:120]!r}") from fel
    if schema not in ("http", "https"):
        raise natvakt.NatvaktError("Bara http- och https-adresser hämtas.")
    # Nätvakten prövar värd, inloggningsuppgifter och DNS; schemat har vi
    # redan godkänt, så adressen ges till den i https-form.
    await natvakt.kontrollera_vard("https" + url[len(schema):])


async def _fore_anrop(request: httpx.Request) -> None:
    try:
        await kontrollera(str(request.url))
    except natvakt.NatvaktError as fel:
        logger.warning("Hämtning spärrad: %s (%s)", request.url.host, fel)
        raise httpx.ConnectError(f"Adressen hämtas inte: {fel}", request=request) from fel


def krokar() -> dict[str, list]:
    """`event_hooks` för en httpx.AsyncClient som hämtar en webbplats."""
    return {"request": [_fore_anrop]}
