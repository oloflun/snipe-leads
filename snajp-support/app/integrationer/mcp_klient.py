"""MCP-klienten: kundens fjärr-MCP-server som verktyg åt support-agenten.

## Vad som stöds

Fjärrtransporterna i Model Context Protocol, som hos Ebbot:
`streamable_http` (standard) och `sse` (äldre servrar). Aldrig stdio: det
vore ett kommando på vår maskin som kunden väljer.

Protokollet sköts av det officiella SDK:t (`mcp`, som redan följer med
openai-agents). SDK:t får däremot INTE sin egen HTTP-klient — vi ger det en
från natvakt, så varje förfrågan det gör (initialize, verktygsanrop,
GET-strömmen, DELETE vid avslut) går genom samma vakt som HTTP-verktygen:
bara publika https-adresser, inga omdirigeringar till interna nät.

## En session per anrop

Varje listning och varje verktygsanrop öppnar en egen session och stänger
den. Det kostar ett par rundturer extra per anrop, men en poolad session per
kund hade varit ett tillstånd att hålla friskt över deploys, workers och
serverns egna tidsgränser — för en agent som gör högst några anrop per ärende
är det fel sida av avvägningen. Verktygslistan cachas däremot (5 min), så
katalogen inte kostar en rundtur per ärende.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from . import natvakt
from .hemligheter import tvatta
from .http_verktyg import SaknatVarde, fyll_text, varden_for
from .modell import McpKonfig
from .resultat import MAX_RESULTATTEXT, Verktygsresultat, kapa

logger = logging.getLogger("snajp-support.integrationer.mcp")

STANDARD_TIDSGRANS = 15.0
CACHE_SEKUNDER = 300.0
MAX_VERKTYG = 64


class McpFel(RuntimeError):
    """Servern gick inte att nå eller svarade fel. Meddelandet går till admin."""


@dataclass(frozen=True)
class McpVerktyg:
    namn: str
    beskrivning: str
    schema: dict[str, Any]
    #: Serverns egna anteckningar (MCP tool annotations). None = omärkt.
    skrivskyddat: bool | None = None
    destruktivt: bool | None = None


def _rubriker(konfig: McpKonfig, hemligheter: dict[str, str]) -> dict[str, str]:
    varden = varden_for(argument={}, hemligheter=hemligheter, kontext={})
    rubriker = {}
    for namn, mall in konfig.headers.items():
        try:
            rubriker[namn] = fyll_text(mall, varden)
        except SaknatVarde as fel:
            raise McpFel(f"Rubriken {namn} refererar en hemlighet som inte är sparad ({fel}).") from fel
    if hemligheter.get("auth"):
        rubriker[konfig.auth_header_name] = hemligheter["auth"]
    return rubriker


@asynccontextmanager
async def _session(
    konfig: McpKonfig, hemligheter: dict[str, str], tidsgrans: float
) -> AsyncIterator[ClientSession]:
    await natvakt.kontrollera_vard(konfig.url)
    rubriker = _rubriker(konfig, hemligheter)
    las_tid = timedelta(seconds=tidsgrans)
    if konfig.transport == "sse":

        def fabrik(headers=None, timeout=None, auth=None):  # noqa: ANN001 — SDK:ts protokoll
            return natvakt.vaktad_klient(headers=headers, tidsgrans=tidsgrans, las_tidsgrans=tidsgrans * 2)

        async with sse_client(
            konfig.url,
            headers=rubriker,
            timeout=tidsgrans,
            sse_read_timeout=tidsgrans * 2,
            httpx_client_factory=fabrik,
        ) as (las, skriv):
            async with ClientSession(las, skriv, read_timeout_seconds=las_tid) as session:
                await session.initialize()
                yield session
        return

    klient = natvakt.vaktad_klient(headers=rubriker, tidsgrans=tidsgrans, las_tidsgrans=tidsgrans * 2)
    async with klient:
        async with streamable_http_client(konfig.url, http_client=klient) as (las, skriv, _):
            async with ClientSession(las, skriv, read_timeout_seconds=las_tid) as session:
                await session.initialize()
                yield session


def _forsta_fel(fel: BaseException) -> BaseException:
    """anyio lindar in fel i ExceptionGroup — beskedet ska gälla det verkliga."""
    while isinstance(fel, BaseExceptionGroup) and fel.exceptions:
        fel = fel.exceptions[0]
    return fel


def _beskriv(fel: BaseException) -> str:
    fel = _forsta_fel(fel)
    if isinstance(fel, natvakt.NatvaktError):
        return f"Adressen är inte tillåten: {fel}"
    if isinstance(fel, McpFel):
        return str(fel)
    if isinstance(fel, (TimeoutError, asyncio.TimeoutError)):
        return "MCP-servern svarade inte i tid."
    status = getattr(getattr(fel, "response", None), "status_code", None)
    if status in (401, 403):
        return f"MCP-servern nekade åtkomst ({status}). Kontrollera nyckeln."
    if status:
        return f"MCP-servern svarade {status}."
    return f"MCP-servern gick inte att nå ({type(fel).__name__})."


async def lista_verktyg(
    konfig: McpKonfig, hemligheter: dict[str, str], *, tidsgrans: float = STANDARD_TIDSGRANS
) -> list[McpVerktyg]:
    """Alla verktyg servern erbjuder. Kastar McpFel med ett begripligt besked."""

    async def inre() -> list[McpVerktyg]:
        ut: list[McpVerktyg] = []
        async with _session(konfig, hemligheter, tidsgrans) as session:
            markor: str | None = None
            for _ in range(5):  # sidor; en server med >5 sidor verktyg är inte en supportintegration
                svar = await session.list_tools(cursor=markor) if markor else await session.list_tools()
                for t in svar.tools:
                    anteckning = t.annotations
                    ut.append(
                        McpVerktyg(
                            namn=t.name,
                            beskrivning=(t.description or t.title or t.name)[:800],
                            schema=dict(t.inputSchema or {"type": "object", "properties": {}}),
                            skrivskyddat=getattr(anteckning, "readOnlyHint", None),
                            destruktivt=getattr(anteckning, "destructiveHint", None),
                        )
                    )
                markor = svar.nextCursor
                if not markor or len(ut) >= MAX_VERKTYG:
                    break
        return ut[:MAX_VERKTYG]

    try:
        return await asyncio.wait_for(inre(), timeout=tidsgrans * 2)
    except (Exception, BaseExceptionGroup) as fel:  # noqa: BLE001
        raise McpFel(_beskriv(fel)) from None


_cache: dict[str, tuple[float, list[McpVerktyg]]] = {}


async def lista_verktyg_cachat(
    nyckel: str, konfig: McpKonfig, hemligheter: dict[str, str]
) -> list[McpVerktyg]:
    """`nyckel` ska ändras när konfigurationen ändras (id + uppdaterad-tid)."""
    nu = time.monotonic()
    traff = _cache.get(nyckel)
    if traff and nu - traff[0] < CACHE_SEKUNDER:
        return traff[1]
    verktyg = await lista_verktyg(konfig, hemligheter)
    _cache[nyckel] = (nu, verktyg)
    return verktyg


def tom_cache() -> None:
    _cache.clear()


def _text_ur(resultat: Any) -> str:
    strukturerat = getattr(resultat, "structuredContent", None)
    if strukturerat:
        return json.dumps(strukturerat, ensure_ascii=False)
    delar: list[str] = []
    for del_ in getattr(resultat, "content", None) or []:
        typ = getattr(del_, "type", "")
        if typ == "text":
            delar.append(del_.text)
        elif typ == "resource":
            text = getattr(getattr(del_, "resource", None), "text", None)
            if text:
                delar.append(text)
        elif typ == "image":
            delar.append("[bild]")
        elif typ == "resource_link":
            delar.append(f"[länk: {getattr(del_, 'uri', '')}]")
    return "\n".join(delar)


async def anropa_verktyg(
    konfig: McpKonfig,
    hemligheter: dict[str, str],
    *,
    verktygsnamn: str,
    serverns_namn: str,
    argument: dict[str, Any] | None,
    skrivande: bool,
    simulera: bool = False,
    tidsgrans: float = STANDARD_TIDSGRANS,
    max_text: int = MAX_RESULTATTEXT,
) -> Verktygsresultat:
    """Kör ett verktyg. Kastar aldrig — fel blir ett resultat med `fel`."""
    start = time.monotonic()

    def resultat(**kw: Any) -> Verktygsresultat:
        return Verktygsresultat(
            verktyg=verktygsnamn,
            skrivande=skrivande,
            latens_ms=int((time.monotonic() - start) * 1000),
            **kw,
        )

    if argument is not None and not isinstance(argument, dict):
        return resultat(ok=False, fel="Argumenten ska vara ett objekt.")
    if simulera and skrivande:
        return resultat(ok=True, simulerad=True, data=f"MCP {serverns_namn}")

    async def inre() -> Any:
        async with _session(konfig, hemligheter, tidsgrans) as session:
            return await session.call_tool(
                serverns_namn, argument or {}, read_timeout_seconds=timedelta(seconds=tidsgrans)
            )

    try:
        svar = await asyncio.wait_for(inre(), timeout=tidsgrans * 2)
    except (Exception, BaseExceptionGroup) as fel:  # noqa: BLE001
        logger.info("MCP-verktyget %s föll: %s", verktygsnamn, type(_forsta_fel(fel)).__name__)
        return resultat(ok=False, fel=_beskriv(fel))

    text = kapa(tvatta(_text_ur(svar), hemligheter), max_text)
    if getattr(svar, "isError", False):
        return resultat(ok=False, data=text, fel=f"Verktyget svarade med ett fel: {text[:300]}")
    return resultat(ok=True, data=text)
