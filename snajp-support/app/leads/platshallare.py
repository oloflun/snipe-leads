"""Platshållarsidor: parkerade domäner, "under konstruktion", domäner till salu.

Uppmätt 2026-09-15 i QA-kundens leadskörning (Nordform): två av fem bolag
fick "inget källmaterial". almapropertypartners.se är parkerad hos Loopia och
itkonsulterna.se visar bara "Under konstruktion"; SAPS Service Management
(2026-09-14) var också parkerad. Ett bolag vars webbplats är en platshållare
har ingen skrapyta, ingen kontaktväg och inget att grunda ett mejl på - det
ska sorteras bort i discovery innan det tar en researchplats, och researchen
ska få veta VARFÖR sidan är tom i stället för att gissa.

Igenkänningen är avsiktligt snäv: en markör räknas bara på en KORT sida. En
riktig sajt som skriver "vårt nya kontor är under konstruktion" har långt mer
text än en parkeringssida.
"""

from __future__ import annotations

import html as _html
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("snajp-support.leads.platshallare")

_MARKORER: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "parkerad domän",
        (
            "parkerad hos",
            "parkerat av en kund",
            "domänen är parkerad",
            "parked at",
            "purchased and parked",
            "domain is parked",
        ),
    ),
    (
        "domänen är till salu",
        ("är till salu", "köp denna domän", "is for sale", "buy this domain"),
    ),
    (
        "under konstruktion",
        ("under konstruktion", "under construction", "kommer snart", "coming soon"),
    ),
    (
        "webbhotellets standardsida",
        ("welcome to nginx", "apache2 default page", "default web site page", "it works!"),
    ),
)

#: Längre text än så här (utan länkadresser) är en riktig sida som råkar
#: nämna en markör. Loopias parkeringssida är ~1 000 tecken.
_MAX_TECKEN = 1500

_SKRIPT_RE = re.compile(r"<(script|style|noscript|template)\b.*?</\1\s*>", re.S | re.I)
_LANK_RE = re.compile(r"<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a\s*>", re.S | re.I)
_RADBRYT_RE = re.compile(r"<(br|/p|/div|/h[1-6]|/li|/tr|/section|/header|/footer)\b[^>]*>", re.I)
_TAGG_RE = re.compile(r"<[^>]+>")
_MD_BILD_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_ADRESS_RE = re.compile(r"\]\([^)]*\)")


def html_till_text(html_text: str) -> str:
    """Läsbar text ur HTML, med länkar kvar som markdown-länkar.

    Länkarna behålls för att kontaktupptäckten (`extrahera_kontaktlankar`)
    letar om-oss- och kontaktsidor i exakt det här materialet.
    """
    if not html_text:
        return ""
    rensad = _SKRIPT_RE.sub(" ", html_text)
    rensad = _LANK_RE.sub(
        lambda m: f"[{' '.join(_TAGG_RE.sub(' ', m.group(2)).split())}]({m.group(1).strip()})",
        rensad,
    )
    rensad = _RADBRYT_RE.sub("\n", rensad)
    text = _html.unescape(_TAGG_RE.sub(" ", rensad))
    rader = (" ".join(rad.split()) for rad in text.splitlines())
    return "\n".join(rad for rad in rader if rad)


def platshallarskal(text: str) -> str | None:
    """Varför sidan är en platshållare ("parkerad domän" ...), eller None."""
    if not text:
        return None
    utan_adresser = _MD_ADRESS_RE.sub("]", _MD_BILD_RE.sub(" ", text))
    rent = " ".join(utan_adresser.split())
    if not rent or len(rent) > _MAX_TECKEN:
        return None
    lag = rent.casefold()
    for skal, markorer in _MARKORER:
        if any(markor in lag for markor in markorer):
            return skal
    return None


def _kontroll_pa() -> bool:
    """Styrs av LEADS_PLATSHALLARKONTROLL. OSATT = på. "0" eller tom = av,
    vilket är testsvitens läge (tests/conftest.py): kontrollen gör riktiga
    HTTP-anrop, och en svit som når internet är grön beroende på vädret."""
    return os.environ.get("LEADS_PLATSHALLARKONTROLL", "1").strip() not in ("", "0")


async def platshallare_for_webbplats(url: str | None) -> str | None:
    """Hämtar startsidan och säger om den är en platshållare. Kastar aldrig;
    ett nätverksfel eller en blockerad sida (403) är INTE en platshållare -
    många riktiga sajter spärrar enkla klienter."""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(6.0, connect=4.0),
            follow_redirects=True,
            headers={"user-agent": "Mozilla/5.0 (compatible; snajp-leads/1.0; +https://snajp.se)"},
        ) as client:
            svar = await client.get(url)
    except httpx.HTTPError:
        return None
    if svar.status_code >= 400:
        return None
    return platshallarskal(html_till_text(svar.text[:400_000]))


async def ar_platshallare(url: str | None) -> str | None:
    """Samma bedömning som `utan_platshallare`, för EN webbplats och med samma
    testlägesbrytare. None när kontrollen är avstängd."""
    if not _kontroll_pa():
        return None
    return await platshallare_for_webbplats(url)


async def utan_platshallare(traffar: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtrerar bort träffar vars webbplats är en platshållare. Ordningen
    behålls; kontrollerna körs parallellt."""
    if not traffar or not _kontroll_pa():
        return traffar
    import asyncio

    skal = await asyncio.gather(*(platshallare_for_webbplats(t.get("website")) for t in traffar))
    kvar: list[dict[str, Any]] = []
    for traff, orsak in zip(traffar, skal):
        if orsak:
            logger.info(
                "Webbplatsen för %s är en platshållare (%s) — förkastas.",
                traff.get("company_name"),
                orsak,
            )
            continue
        kvar.append(traff)
    return kvar
