"""Nätvakten: vart en kundkonfigurerad integration får ringa, och hur mycket.

## Varför den finns

En integration är en URL som KUNDEN skriver in och som VÅR server sedan
anropar. Utan vakt är det en SSRF-yta: `http://169.254.169.254/` (molnets
metadatatjänst), `http://localhost:8000/api/admin/...` eller en intern
Railway-adress hade nåtts inifrån vårt nät, med svaret inläst i en prompt och
kanske återgivet för kunden. Samma sak med ett MCP-endpoint och med en
kanal-API-adress ur en inkommande webhook.

Reglerna följer Ebbots publicerade gränser för sitt http_request-verktyg
(bara HTTPS, ingen localhost, inga privata IP, inga enkelledade värdnamn,
inga .local, högst 3 omdirigeringar, 1 MB, 15 s) — med en skärpning: VARJE
omdirigering valideras på nytt, och en omdirigering till en annan värd tar
inte med sig rubrikerna (där hemligheterna sitter).

## Vad den INTE skyddar mot

DNS-ombindning i fönstret mellan vår uppslagning och anslutningen: värden
slås upp och kontrolleras här, och httpx slår upp den igen när den ansluter.
Ett namn som byter svar på millisekunder kan i teorin glida igenom. Fönstret
är litet, och det enda som når fram är ett anrop med kundens EGNA hemligheter
— våra ligger inte i rubrikerna. Täppa till det (anslut mot den kontrollerade
adressen med SNI satt) den dag vi har en anledning att tro att någon försöker.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

import httpx

#: Ebbots gränser, se modulens docstring.
MAX_SVARSSTORLEK = 1_000_000
MAX_OMDIRIGERINGAR = 3
STANDARD_TIDSGRANS = 15.0

#: Svarstyper som får läsas in. Binärt (bilder, PDF, zip) har inget i en
#: prompt att göra, och att läsa in en megabyte brus är bara latens.
_TILLATNA_TYPER = (
    "application/json",
    "application/problem+json",
    "application/ld+json",
    "application/hal+json",
    "application/xml",
    "application/x-ndjson",
    "text/",
)

_FORBJUDNA_SUFFIX = (".local", ".localhost", ".internal", ".home.arpa", ".lan", ".intranet", ".corp")
_FORBJUDNA_VARDAR = {"localhost", "metadata", "metadata.google.internal"}


class NatvaktError(ValueError):
    """Adressen eller svaret är inte tillåtet. Meddelandet går till admin."""


def _ip_tillatet(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Bara globalt routbara adresser.

    `is_global` täcker privata nät, loopback, länklokalt (där metadata-
    tjänsten bor), CGNAT (100.64/10), dokumentationsnät och reserverat. En
    IPv4-mappad IPv6-adress (::ffff:10.0.0.1) prövas som den IPv4 den är.
    """
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return bool(ip.is_global) and not ip.is_multicast


def kontrollera_url(url: str) -> str:
    """Formkontroll utan nätverk: schema, värdnamn, inga inloggningsuppgifter.

    Returnerar värdnamnet (gemener). Kastar NatvaktError.
    """
    try:
        delar = urlsplit(url)
    except ValueError as fel:
        raise NatvaktError(f"Ogiltig adress: {url[:120]!r}") from fel
    if delar.scheme.lower() != "https":
        raise NatvaktError("Bara https-adresser är tillåtna.")
    if delar.username or delar.password:
        raise NatvaktError("Adressen får inte innehålla inloggningsuppgifter (användare@).")
    vard = (delar.hostname or "").strip().lower().rstrip(".")
    if not vard:
        raise NatvaktError("Adressen saknar värdnamn.")
    try:
        ip = ipaddress.ip_address(vard)
    except ValueError:
        ip = None
    if ip is not None:
        if not _ip_tillatet(ip):
            raise NatvaktError("Adressen pekar på ett internt eller reserverat nät.")
        return vard
    if vard in _FORBJUDNA_VARDAR or vard.endswith(_FORBJUDNA_SUFFIX):
        raise NatvaktError(f"Värden {vard!r} är en intern adress.")
    if "." not in vard:
        raise NatvaktError(f"Värden {vard!r} är inte ett fullständigt domännamn.")
    return vard


Upplosare = Callable[[str, int], Awaitable[list[str]]]


async def _dns(vard: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    svar = await loop.getaddrinfo(vard, port, type=socket.SOCK_STREAM)
    return [s[4][0] for s in svar]


#: Utbytbar i testsviten (tests/integrationer): testerna ska inte bero på DNS.
upplos: Upplosare = _dns


async def kontrollera_vard(url: str) -> None:
    """Formkontroll + DNS: ALLA adresser värden löser upp till måste vara globala.

    "Alla" och inte "någon": ett namn med en publik och en privat A-post
    skulle annars kunna passera kontrollen och ansluta till den privata.
    """
    vard = kontrollera_url(url)
    try:
        ipaddress.ip_address(vard)
        return  # IP-literal, redan prövad
    except ValueError:
        pass
    port = urlsplit(url).port or 443
    try:
        adresser = await upplos(vard, port)
    except OSError as fel:
        raise NatvaktError(f"Värden {vard!r} gick inte att slå upp.") from fel
    if not adresser:
        raise NatvaktError(f"Värden {vard!r} gick inte att slå upp.")
    for adress in adresser:
        try:
            ip = ipaddress.ip_address(adress.split("%", 1)[0])
        except ValueError as fel:
            raise NatvaktError(f"Värden {vard!r} gav en oläsbar adress.") from fel
        if not _ip_tillatet(ip):
            raise NatvaktError(f"Värden {vard!r} pekar på ett internt nät.")


def _standardtransport() -> httpx.AsyncBaseTransport:
    return httpx.AsyncHTTPTransport(retries=0)


#: Fabrik för den INRE transporten. Testsviten byter den mot en
#: httpx.MockTransport eller en ASGI-transport; vakten ligger utanpå oavsett.
inre_transport: Callable[[], httpx.AsyncBaseTransport] = _standardtransport


class VaktadTransport(httpx.AsyncBaseTransport):
    """Kör `kontrollera_vard` före VARJE förfrågan klienten gör.

    Ligger i transporten och inte i anroparen för att täcka det anroparen
    inte ser: MCP-SDK:ns egna förfrågningar (initialize, GET-strömmen,
    DELETE vid avslut) går alla genom samma klient.
    """

    def __init__(self, inre: httpx.AsyncBaseTransport | None = None) -> None:
        self._inre = inre or inre_transport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await kontrollera_vard(str(request.url))
        return await self._inre.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inre.aclose()


def vaktad_klient(
    *,
    headers: dict[str, str] | None = None,
    tidsgrans: float = STANDARD_TIDSGRANS,
    las_tidsgrans: float | None = None,
) -> httpx.AsyncClient:
    """En httpx-klient som bara når publika https-adresser och aldrig följer
    omdirigeringar själv (det gör `anropa`, med ny kontroll per hopp)."""
    return httpx.AsyncClient(
        transport=VaktadTransport(),
        follow_redirects=False,
        headers=headers,
        timeout=httpx.Timeout(tidsgrans, read=las_tidsgrans or tidsgrans),
    )


@dataclass
class Svar:
    url: str
    metod: str
    status: int
    status_text: str
    innehallstyp: str
    text: str
    rubriker: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def _typ_tillaten(innehallstyp: str) -> bool:
    typ = innehallstyp.split(";", 1)[0].strip().lower()
    return not typ or typ.startswith(_TILLATNA_TYPER) or typ.endswith("+json") or typ.endswith("+xml")


async def anropa(
    metod: str,
    url: str,
    *,
    rubriker: dict[str, str] | None = None,
    json_kropp: object | None = None,
    innehall: bytes | None = None,
    tidsgrans: float = STANDARD_TIDSGRANS,
    max_storlek: int = MAX_SVARSSTORLEK,
) -> Svar:
    """Ett vaktat HTTP-anrop, med omdirigeringar följda för hand.

    - 301/302/303 blir GET utan kropp (som i en webbläsare), 307/308 behåller
      metod och kropp.
    - En omdirigering till en ANNAN värd skickas utan rubriker: där sitter
      kundens nycklar, och de gavs till den första värden, inte till vem den
      pekar vidare på.
    - Svaret läses strömmande och avbryts vid `max_storlek`.
    """
    metod = metod.upper()
    rubriker = dict(rubriker or {})
    nuvarande = url
    ursprungsvard = kontrollera_url(url)
    async with vaktad_klient(tidsgrans=tidsgrans) as klient:
        for hopp in range(MAX_OMDIRIGERINGAR + 1):
            forfragan = klient.build_request(
                metod,
                nuvarande,
                headers=rubriker,
                json=json_kropp if innehall is None and json_kropp is not None else None,
                content=innehall,
            )
            svar = await klient.send(forfragan, stream=True)
            try:
                if svar.is_redirect:
                    if hopp >= MAX_OMDIRIGERINGAR:
                        raise NatvaktError(f"Fler än {MAX_OMDIRIGERINGAR} omdirigeringar.")
                    plats = svar.headers.get("location") or ""
                    if not plats:
                        raise NatvaktError("Omdirigering utan adress.")
                    nasta = urljoin(nuvarande, plats)
                    if kontrollera_url(nasta) != ursprungsvard:
                        rubriker = {}
                    if svar.status_code in (301, 302, 303):
                        metod, json_kropp, innehall = "GET", None, None
                    nuvarande = nasta
                    continue

                innehallstyp = svar.headers.get("content-type", "")
                if not _typ_tillaten(innehallstyp):
                    raise NatvaktError(
                        f"Svaret är av typen {innehallstyp.split(';')[0]!r}, som inte läses in."
                    )
                delar: list[bytes] = []
                storlek = 0
                async for bit in svar.aiter_bytes():
                    storlek += len(bit)
                    if storlek > max_storlek:
                        raise NatvaktError(f"Svaret är större än {max_storlek // 1000} kB.")
                    delar.append(bit)
                kropp = b"".join(delar)
                kodning = svar.charset_encoding or "utf-8"
                return Svar(
                    url=str(svar.request.url),
                    metod=metod,
                    status=svar.status_code,
                    status_text=svar.reason_phrase or "",
                    innehallstyp=innehallstyp,
                    text=kropp.decode(kodning, errors="replace"),
                    rubriker={k.lower(): v for k, v in svar.headers.items()},
                )
            finally:
                await svar.aclose()
    raise NatvaktError("Omdirigeringskedjan tog aldrig slut.")  # pragma: no cover
