"""Mätta fakta om ett bolags webbplats — inte modellens intryck.

Alunix (webbyrå) söker bolag med "gamla, dåligt optimerade hemsidor eller
ingen sida alls". Att låta modellen bedöma det ur skrapad TEXT är en gissning:
texten säger inget om mobilanpassning eller svarstid. Här mäts det i kod, och
varje fakta blir en rad modellen kan citera som belägg och utkastet får nämna
(grundningsgrinden släpper bara igenom det som står i underlaget).

En ren funktion (`analysera`) över HTML + headers + svarstid, och en tunn
hämtare runt den. Hämtningen gäller bolagets EGEN startsida, som redan är
registrerad källa för prospektet.
"""

from __future__ import annotations

import os
import re
import time
from datetime import date
from typing import Any

import httpx

_TIMEOUT = 10.0
_AR = re.compile(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", re.IGNORECASE)
_GENERATOR = re.compile(r"<meta[^>]+name=[\"']generator[\"'][^>]+content=[\"']([^\"']+)", re.IGNORECASE)
_JQUERY = re.compile(r"jquery[.-]?(\d+\.\d+(?:\.\d+)?)(?:\.min)?\.js", re.IGNORECASE)
_VIEWPORT = re.compile(r"<meta[^>]+name=[\"']viewport[\"']", re.IGNORECASE)

#: Plattformar som syns i markupen även utan generator-tagg.
_PLATTFORMAR = (
    ("Wix", re.compile(r"static\.wixstatic\.com|wix-code|_wixCIDX", re.I)),
    ("Squarespace", re.compile(r"squarespace\.com|static1\.squarespace", re.I)),
    ("Webflow", re.compile(r"data-wf-page|webflow\.js|assets\.website-files\.com", re.I)),
    ("Next.js", re.compile(r"/_next/static/|__NEXT_DATA__", re.I)),
    ("WordPress", re.compile(r"/wp-content/|/wp-includes/", re.I)),
    ("Joomla", re.compile(r"/media/jui/|joomla", re.I)),
    ("Shopify", re.compile(r"cdn\.shopify\.com", re.I)),
)
#: Rörelse: bibliotek och CSS-mekanismer som bara finns på sajter med animationer.
_ANIMATION = re.compile(
    r"gsap|scrolltrigger|framer-motion|lottie|aos\.js|data-aos=|swiper|splide|locomotive-scroll|lenis|"
    r"@keyframes|animation\s*:|scroll-behavior\s*:\s*smooth|IntersectionObserver",
    re.I,
)
_MODERN_LAYOUT = re.compile(r"display\s*:\s*(flex|grid)|\b(d-flex|flex|grid|grid-cols-\d+)\b", re.I)
_MODERNA_BILDER = re.compile(r"\.(webp|avif)\b|<picture\b|srcset=", re.I)
_NAV_LANK = re.compile(r"<nav\b.*?</nav>", re.I | re.S)


def analysera(
    *, url: str | None, html: str | None, headers: dict[str, str] | None = None,
    svarstid_s: float | None = None, idag: date | None = None,
) -> dict[str, Any]:
    """Fakta ur en hämtad startsida. `rader` är den citerbara formen."""
    idag = idag or date.today()
    if not url or html is None:
        return {"har_webbplats": False, "rader": ["Ingen webbplats hittades för bolaget."]}
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    rader: list[str] = []
    fakta: dict[str, Any] = {"har_webbplats": True, "url": url}

    fakta["https"] = url.lower().startswith("https://")
    if not fakta["https"]:
        rader.append("Webbplatsen saknar https (krypterad anslutning).")

    fakta["mobilanpassad"] = bool(_VIEWPORT.search(html))
    if not fakta["mobilanpassad"]:
        rader.append("Startsidan saknar viewport-inställning, alltså ingen mobilanpassning.")

    ar = [int(a) for a in _AR.findall(html) if 1990 <= int(a) <= idag.year]
    if ar:
        fakta["copyright_ar"] = max(ar)
        if idag.year - max(ar) >= 2:
            rader.append(f"Sidfoten anger copyright {max(ar)}.")

    gen = _GENERATOR.search(html)
    if gen:
        fakta["generator"] = gen.group(1).strip()[:80]
        rader.append(f"Webbplatsen är byggd med {fakta['generator']}.")

    jq = _JQUERY.search(html)
    if jq:
        fakta["jquery"] = jq.group(1)
        if int(jq.group(1).split(".")[0]) < 3:
            rader.append(f"Webbplatsen använder jQuery {jq.group(1)}, en äldre version.")

    plattform = next((namn for namn, m in _PLATTFORMAR if m.search(html)), None)
    if plattform:
        fakta["plattform"] = plattform
        if not gen:
            rader.append(f"Webbplatsen är byggd med {plattform}.")
    fakta["animationer"] = bool(_ANIMATION.search(html))
    fakta["modern_layout"] = bool(_MODERN_LAYOUT.search(html))
    fakta["moderna_bilder"] = bool(_MODERNA_BILDER.search(html))
    if not fakta["animationer"]:
        rader.append("Startsidan har inga animationer eller rörliga element.")
    if not fakta["moderna_bilder"] and "<img" in html.lower():
        rader.append("Bilderna saknar moderna format och storleksanpassning (webp, avif, srcset).")
    nav = _NAV_LANK.search(html)
    if nav:
        fakta["menyval"] = len(re.findall(r"<a\b", nav.group(0), re.I))

    fakta["sidvikt_kb"] = round(len(html.encode("utf-8", "ignore")) / 1024)
    if svarstid_s is not None:
        fakta["svarstid_s"] = round(svarstid_s, 1)
        if svarstid_s >= 3:
            rader.append(f"Startsidan tog {fakta['svarstid_s']} sekunder att svara.")

    if "<table" in html.lower() and html.lower().count("<table") >= 3 and "<div" not in html.lower()[:5000]:
        rader.append("Startsidans layout är byggd med tabeller.")
    if "last-modified" in headers:
        fakta["last_modified"] = headers["last-modified"]

    if not rader:
        rader.append("Inga tecken på föråldrad teknik hittades på startsidan.")
    fakta["rader"] = rader
    fakta["utdrag"] = synlig_text(html)
    return fakta


async def mat_webbplats(url: str | None) -> dict[str, Any]:
    """Hämtar startsidan och analyserar den. Kastar aldrig: en sajt som inte
    svarar är i sig en signal."""
    if not url:
        return analysera(url=None, html=None)
    # LEADS_WEBBSIGNAL: OSATT = på, tom/"0" = av — testsvitens läge
    # (tests/conftest.py), samma mönster som platshållarkontrollen.
    #
    # `matt` säger om sidan faktiskt hämtades. Existensgrinden
    # (leads/existens.py) fäller bara på en MÄTNING: `svarar_inte` (DNS-fel,
    # timeout) eller `http_status` (felsvar). Före 2026-10-06 såg en domän
    # som inte finns likadan ut som en långsam sajt, och tre påhittade bolag
    # gick vidare till research.
    if os.environ.get("LEADS_WEBBSIGNAL", "1").strip() in ("", "0"):
        return {"har_webbplats": True, "url": url, "rader": [], "utdrag": "", "matt": False}
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            svar = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Snajp Iris)"})
        tid = time.monotonic() - start
        if svar.status_code >= 400:
            return {"har_webbplats": True, "url": url, "matt": True, "http_status": svar.status_code,
                    "rader": [f"Startsidan svarade med fel ({svar.status_code})."]}
        html = svar.text[:400_000]
        return {
            **analysera(url=str(svar.url), html=html, headers=dict(svar.headers), svarstid_s=tid),
            "matt": True,
            # Hela sidans synliga text (utdraget är kapat vid 3 000 tecken, och
            # bolagsnamnet står ofta bara i sidfoten).
            "sidtext": synlig_text(html, tak=200_000),
        }
    except httpx.HTTPError:
        return {"har_webbplats": True, "url": url, "matt": True, "svarar_inte": True,
                "rader": [f"Startsidan svarade inte inom {int(_TIMEOUT)} sekunder."]}


_SKRIPT = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAGG = re.compile(r"<[^>]+>")


def synlig_text(html: str, tak: int = 3000) -> str:
    """Startsidans synliga text, en rad per block — utdraget Jev-triagen
    läser. Grovt med flit: det ska bara räcka för att se vad bolaget gör."""
    text = _TAGG.sub("\n", _SKRIPT.sub(" ", html or ""))
    rader = [re.sub(r"\s+", " ", r).strip() for r in text.splitlines()]
    return "\n".join(r for r in rader if len(r) >= 3)[:tak]


def som_text(fakta: dict[str, Any]) -> str:
    return "## MÄTTA WEBBSIGNALER (uppmätt av Snajp, citerbara som belägg)\n" + "\n".join(
        f"- {r}" for r in fakta.get("rader") or []
    )


def demo() -> None:
    gammal = analysera(
        url="http://exempel.se",
        html="<html><table></table><table></table><table></table>© 2013 Exempel<script src='jquery-1.8.3.min.js'></script>",
        svarstid_s=4.2,
        idag=date(2026, 9, 30),
    )
    assert not gammal["https"] and not gammal["mobilanpassad"] and gammal["copyright_ar"] == 2013
    assert any("jQuery 1.8.3" in r for r in gammal["rader"])
    ny = analysera(
        url="https://ny.se",
        html='<meta name="viewport" content="x"><div class="grid">© 2026</div><script src="/_next/static/a.js">'
        '</script><style>@keyframes in{}</style><img srcset="a.webp 1x">',
        idag=date(2026, 9, 30),
    )
    assert ny["rader"] == ["Webbplatsen är byggd med Next.js."]
    assert ny["animationer"] and ny["modern_layout"] and ny["moderna_bilder"]
    assert "Startsidan har inga animationer eller rörliga element." in gammal["rader"]
    assert analysera(url=None, html=None)["har_webbplats"] is False
    print("webbsignal: ok")


if __name__ == "__main__":
    demo()
