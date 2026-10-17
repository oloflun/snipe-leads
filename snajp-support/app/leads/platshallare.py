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
from ..tls import ssl_kontext

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
        ("under konstruktion", "under construction", "under uppbyggnad", "kommer snart", "coming soon"),
    ),
    (
        "webbhotellets standardsida",
        ("welcome to nginx", "apache2 default page", "default web site page", "it works!"),
    ),
    # Facit 2026-10-08: Netlify ("Site not found") och Wix ("Error: page not
    # found") svarar med en felsida på sajtens adress, Kanotcentrum visar bara
    # en fillistning. Alla tre är akuta leads för en webbyrå.
    (
        "felsida",
        ("site not found", "page not found", "this page isn't available", "sidan kunde inte hittas",
         "sidan finns inte", "404 not found", "error 404"),
    ),
    ("fillistning", ("index of /",)),
    (
        # Såg & Betong 2026-10-08. Ett avvecklat bolag är inget lead alls:
        # det kastas i stället för att bli en akut webbsajt (Anton).
        "bolaget avvecklas",
        ("under avveckling", "bedriver inte längre", "försatt i konkurs", "har upphört med sin verksamhet",
         "verksamheten är avvecklad", "verksamheten har avvecklats", "har lagt ner verksamheten"),
    ),
)

#: Skälet som betyder att bolaget ska kastas, inte bli ett akut lead.
AVVECKLAT = "bolaget avvecklas"

#: Längre text än så här (utan länkadresser) är en riktig sida som råkar
#: nämna en markör. Loopias parkeringssida är ~1 000 tecken.
_MAX_TECKEN = 1500

_SKRIPT_RE = re.compile(r"<(script|style|noscript|template)\b.*?</\1\s*>", re.S | re.I)
_LANK_RE = re.compile(r"<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a\s*>", re.S | re.I)
_RADBRYT_RE = re.compile(r"<(br|/p|/div|/h[1-6]|/li|/tr|/section|/header|/footer)\b[^>]*>", re.I)
_TAGG_RE = re.compile(r"<[^>]+>")
_MD_BILD_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_ADRESS_RE = re.compile(r"\]\([^)]*\)")

#: Cloudflares adresskydd: adressen står XOR-kodad i ett attribut eller i
#: länkens fragment, och sidans text säger bara "[email protected]". Utan
#: avkodningen gav en skyddad sajt aldrig en kontakt (Antons regel 12,
#: 2026-10-07: en sajt har alltid ett kontaktsätt, vi måste hitta det).
_CFEMAIL_ELEMENT = re.compile(
    r"""<(a|span)\b[^>]*\bdata-cfemail\s*=\s*["']([0-9a-fA-F]+)["'][^>]*>.*?</\1\s*>""", re.S | re.I
)
#: Värddatorn före sökvägen är valfri och avgränsad. Före 2026-10-09 började
#: mönstret med ett oankrat [^"'\s>]*: på en sida med en lång rad utan
#: citattecken (inbäddad base64, minifierat skript) skannade varje startposition
#: hela raden, och optera.se (197 kB) låste api-processens händelseloop i två
#: minuter, chatten och alla körningar med den.
_CFEMAIL_HREF = re.compile(
    r"""(?:(?:https?:)?//[^"'\s>/]{1,253})?/cdn-cgi/l/email-protection#([0-9a-fA-F]+)""", re.I
)
#: JSON-LD (schema.org) bär ofta bolagets e-post och telefon, men ligger i ett
#: script som taggstrippen tar bort.
_JSONLD_RE = re.compile(r"""<script\b[^>]*type\s*=\s*["']application/ld\+json["'][^>]*>(.*?)</script\s*>""", re.S | re.I)
_JSONLD_FALT = re.compile(r""""(email|telephone)"\s*:\s*"([^"]{3,100})\"""", re.I)
_MAILTO_HREF = re.compile(r"""href\s*=\s*["']mailto:([^"'?>]+)""", re.I)
_TEL_HREF = re.compile(r"""href\s*=\s*["']tel:([^"'>]+)""", re.I)


def _cf_avkoda(hexa: str) -> str:
    """Cloudflares kodning: första byten är nyckeln, resten XOR-as med den."""
    try:
        data = bytes.fromhex(hexa)
    except ValueError:
        return ""
    if len(data) < 2:
        return ""
    return bytes(b ^ data[0] for b in data[1:]).decode("utf-8", errors="ignore")


def avkoda_cfemail(html_text: str) -> str:
    """Skyddade adresser skrivs ut på sin plats: elementet blir adressen och
    länken blir en mailto-länk. Närheten till namnet bevaras därmed."""
    if not html_text or ("cfemail" not in html_text and "email-protection" not in html_text):
        return html_text or ""
    text = _CFEMAIL_ELEMENT.sub(lambda m: _cf_avkoda(m.group(2)), html_text)
    return _CFEMAIL_HREF.sub(lambda m: "mailto:" + _cf_avkoda(m.group(1)), text)


def kontaktrader_ur_html(html_text: str) -> list[str]:
    """E-post och telefon ur det som taggstrippen tar bort (JSON-LD,
    mailto- och tel-länkar, Cloudflare-skyddade adresser), som rader
    "E-post: x" och "Telefon: y". De läggs till sidans text och följer
    därmed med in i cachen."""
    from urllib.parse import unquote

    if not html_text:
        return []
    epost: list[str] = [_cf_avkoda(m.group(2)) for m in _CFEMAIL_ELEMENT.finditer(html_text)]
    epost += [_cf_avkoda(hexa) for hexa in _CFEMAIL_HREF.findall(html_text)]
    html_text = avkoda_cfemail(html_text)
    telefon: list[str] = []
    for block in _JSONLD_RE.findall(html_text):
        for falt, varde in _JSONLD_FALT.findall(block):
            (epost if falt.lower() == "email" else telefon).append(varde)
    epost += _MAILTO_HREF.findall(html_text)
    telefon += _TEL_HREF.findall(html_text)
    rader: list[str] = []
    for etikett, varden in (("E-post", epost), ("Telefon", telefon)):
        for varde in varden:
            ren = unquote(_html.unescape(varde)).strip()
            ren = ren[len("mailto:"):] if ren.lower().startswith("mailto:") else ren
            rad = f"{etikett}: {ren}"
            if ren and rad not in rader:
                rader.append(rad)
    return rader


def html_till_text(html_text: str) -> str:
    """Läsbar text ur HTML, med länkar kvar som markdown-länkar.

    Länkarna behålls för att kontaktupptäckten (`extrahera_kontaktlankar`)
    letar om-oss- och kontaktsidor i exakt det här materialet. Kontaktrader
    ur attribut och JSON-LD (`kontaktrader_ur_html`) läggs till sist.
    """
    if not html_text:
        return ""
    kontaktrader = kontaktrader_ur_html(html_text)
    rensad = _SKRIPT_RE.sub(" ", avkoda_cfemail(html_text))
    rensad = _LANK_RE.sub(
        lambda m: f"[{' '.join(_TAGG_RE.sub(' ', m.group(2)).split())}]({m.group(1).strip()})",
        rensad,
    )
    rensad = _RADBRYT_RE.sub("\n", rensad)
    text = _html.unescape(_TAGG_RE.sub(" ", rensad))
    rader = [" ".join(rad.split()) for rad in text.splitlines()]
    return "\n".join([*(rad for rad in rader if rad), *kontaktrader])


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
            verify=ssl_kontext(),
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
