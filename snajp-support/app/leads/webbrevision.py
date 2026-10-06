"""Webbrevision: hur bolagets sajt ser ut och presterar (plan 2026-10-05, fas 3).

Antons granskning 2026-10-04 av Alunix-leadsen: Björkekärr Bygg och Eustaff
har bra, moderna sajter men fick ändå starka betyg för "gamla hemsidor", medan
Byggarna Berggren (en logga och en kontaktrad) och Vicht träffade rätt. Skälet
var att bedömningen byggde på skrapad TEXT och några grova signaler
(copyright-år, generator, svarstid). Text säger inget om hur en sida ser ut.

Här görs det i två steg som båda är gratis eller nästan gratis:

1. **Google PageSpeed Insights** (gratis, med eller utan nyckel) ger
   Lighthouse-poäng för prestanda, tillgänglighet och SEO, laddtiden för
   största innehållet och en slutlig skärmbild. Siffrorna är dessutom
   säljargument: "er sida tar 7,8 s att ladda på mobil".
2. **Bildbedömning** av skärmbilden med den vision-sidovagn som redan finns
   (`agent.llm.get_vision_client`, samma underbiträde som kvitton och
   kundbilder). Publika bolagssajter är ingen kunddata, så dataskydds-
   beslutet om DeepSeek berörs inte. Kodens mätta signaler (animationer,
   layout, plattform) skickas med som fakta: en skärmbild kan inte se rörelse.

Resultatet är fakta och ett betyg, aldrig ett fritt omdöme som får avgöra
ensamt: `bedomning.webbutslag` översätter betyget till träff, miss eller
okänt i kod.

LEADS_WEBBREVISION: osatt = på (drift), tom sträng = av (testsviten, nionde
gången samma läxa — conftest tömmer den).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("snajp-support.leads.webbrevision")

PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PSI_TIMEOUT = httpx.Timeout(90.0, connect=10.0)

_LAYOUT_TEXT = {
    "tabeller": "tabellbaserad layout",
    "tidig_responsiv": "tidig responsiv design",
    "modern": "modern layout",
}

VISIONPROMPT = """You audit the website of a small Swedish company for a web design agency \
that sells new websites. Judge only what you can see in the screenshot plus the measured facts.

Return ONLY a JSON object with these keys:
- navigering_tydlig: true/false — is there a clear, visible navigation menu?
- hero_modern: true/false — does the top section look current (large imagery or strong \
typography, clear message, call to action)?
- layout_era: "tabeller" | "tidig_responsiv" | "modern"
- typografi_och_luft: "bra" | "medel" | "dalig" — font sizes, hierarchy, whitespace
- bildkvalitet: "bra" | "medel" | "dalig"
- fortroende: "bra" | "medel" | "dalig" — contact details, references, professional finish
- uppskattat_byggar: integer year the design most likely dates from, or null
- modernitet: integer 1-10
- top_3_brister: up to 3 short, concrete, VISIBLE design flaws written in Swedish; [] if none \
worth raising with the owner
- intern_eller_internationell: "lokal" | "internationell" | "okand" — "internationell" if the site \
presents an international group, offices in several countries, or is English-only

Calibration for modernitet:
1-2 = a logo and a contact line, no navigation, or a parked/placeholder page.
3-4 = a dated template (around 2012-2017): small fonts, cluttered header, stock photos, sliders.
5-6 = a clean, responsive but generic template.
7-8 = a crafted, current site: strong typography, consistent spacing, good imagery.
9-10 = agency-grade work with motion, scroll effects and a distinct visual identity.
Animations cannot be seen in a screenshot: trust the measured facts for motion."""


def aktiv() -> bool:
    return os.environ.get("LEADS_WEBBREVISION") != ""


def _poang(lh: dict[str, Any], kategori: str) -> int | None:
    score = ((lh.get("categories") or {}).get(kategori) or {}).get("score")
    return round(score * 100) if isinstance(score, (int, float)) else None


async def pagespeed(url: str, strategi: str) -> dict[str, Any] | None:
    """Lighthouse via PageSpeed Insights, eller None. Kastar aldrig."""
    from ..config import get_settings

    params: list[tuple[str, str]] = [("url", url), ("strategy", strategi)]
    params += [("category", k) for k in ("performance", "accessibility", "seo")]
    nyckel = get_settings().pagespeed_api_key
    if nyckel:
        params.append(("key", nyckel))
    try:
        async with httpx.AsyncClient(timeout=PSI_TIMEOUT) as client:
            svar = await client.get(PSI_URL, params=params)
        if svar.status_code != 200:
            logger.info("PageSpeed %s för %s: HTTP %s", strategi, url, svar.status_code)
            return None
        lh = svar.json().get("lighthouseResult") or {}
    except (httpx.HTTPError, ValueError) as fel:
        logger.info("PageSpeed %s för %s föll: %s", strategi, url, type(fel).__name__)
        return None
    audits = lh.get("audits") or {}
    lcp = (audits.get("largest-contentful-paint") or {}).get("numericValue")
    bild = ((audits.get("final-screenshot") or {}).get("details") or {}).get("data")
    return {
        "prestanda": _poang(lh, "performance"),
        "tillganglighet": _poang(lh, "accessibility"),
        "seo": _poang(lh, "seo"),
        "lcp_s": round(lcp / 1000, 1) if isinstance(lcp, (int, float)) else None,
        "skarmbild": bild if isinstance(bild, str) and bild.startswith("data:image") else None,
    }


def _som_data_url(varde: Any) -> str | None:
    if isinstance(varde, dict):
        varde = varde.get("url") or varde.get("data") or varde.get("base64")
    if not isinstance(varde, str) or not varde:
        return None
    if varde.startswith("data:image"):
        return varde
    if varde.startswith("http"):
        return None  # hämtas av anroparen
    return f"data:image/jpeg;base64,{varde}"


async def skarmbild_via_scrapegraph(url: str) -> str | None:
    """Reserv när PageSpeed inte ger en skärmbild: ScrapeGraphs screenshot-
    format (2 krediter). Räknas mot körningens kredittak. Kastar aldrig."""
    import base64

    from ..config import get_settings
    from . import sidhamtning

    nyckel = get_settings().scrapegraphai_api_key
    kontext = sidhamtning.aktuell()
    if not nyckel or (kontext and kontext.tak - kontext.totalt < 2):
        return None
    try:
        from scrapegraph_py import ScrapeGraphAI, ScreenshotFormatConfig

        client = ScrapeGraphAI(api_key=nyckel)
        if kontext:
            kontext.anrop["skarmbild"] = kontext.anrop.get("skarmbild", 0) + 2
        svar = await asyncio.wait_for(
            asyncio.to_thread(client.scrape, url, formats=[ScreenshotFormatConfig(width=1440, height=900)]),
            timeout=60,
        )
        data = ((svar.data.results or {}).get("screenshot") or {}).get("data") if svar.status == "success" else None
    except Exception as fel:  # noqa: BLE001
        logger.info("Skärmbilden via ScrapeGraph för %s föll: %s", url, type(fel).__name__)
        return None
    bild = _som_data_url(data)
    lank = data.get("url") if isinstance(data, dict) else data
    if bild is None and isinstance(lank, str) and lank.startswith("http"):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(lank)
            if r.status_code == 200:
                typ = (r.headers.get("content-type") or "image/png").split(";")[0]
                bild = f"data:{typ};base64,{base64.b64encode(r.content).decode()}"
        except httpx.HTTPError:
            return None
    return bild


def _json_ur(text: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _fakta_for_modellen(fakta: dict[str, Any]) -> str:
    rader = [f"- {r}" for r in fakta.get("rader") or []]
    for nyckel, text in (
        ("animationer", "Animationer eller scrolleffekter i koden"),
        ("modern_layout", "Flexbox/grid i koden"),
        ("moderna_bilder", "Moderna bildformat (webp/avif/srcset)"),
        ("mobilanpassad", "Viewport för mobil"),
    ):
        if nyckel in fakta:
            rader.append(f"- {text}: {'ja' if fakta[nyckel] else 'nej'}")
    return "\n".join(rader) or "- (inga mätta fakta)"


async def visuell(url: str, skarmbild: str, fakta: dict[str, Any]) -> dict[str, Any] | None:
    """Bildbedömningen som dict, eller None. Kastar aldrig."""
    from ..agent.llm import get_vision_client
    from ..config import get_settings

    client = get_vision_client()
    if client is None:
        return None
    text = f"{VISIONPROMPT}\n\nWebsite: {url}\nMeasured facts:\n{_fakta_for_modellen(fakta)}"
    try:
        svar = await client.chat.completions.create(
            model=get_settings().vision_model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": skarmbild}},
            ]}],
            # gemini-2.5-flash räknar sitt tänkande mot taket: med 600 klipptes
            # JSON-svaret mitt i (kalibreringen 2026-10-05).
            max_tokens=4000,
        )
    except Exception as fel:  # noqa: BLE001 — utan bedömning faller kriteriet tillbaka på texten
        logger.info("Bildbedömningen av %s föll: %s", url, type(fel).__name__)
        return None
    from ..agentcore.insyn import logga_anrop

    # Insynen (Fas 7): textdelen av prompten och svaret. Skärmbilden själv
    # (en data-url på hundratals kB) loggas inte.
    logga_anrop(
        "webbrevision",
        prompt=text,
        svar=svar.choices[0].message.content or "",
        modell=get_settings().vision_model,
        kallor=[url],
    )
    data = _json_ur(svar.choices[0].message.content or "")
    if not data or not isinstance(data.get("modernitet"), (int, float)):
        return None
    data["modernitet"] = max(1, min(10, int(data["modernitet"])))
    data["top_3_brister"] = [str(b).strip() for b in data.get("top_3_brister") or [] if str(b).strip()][:3]
    return data


def citerbara_rader(rev: dict[str, Any]) -> list[str]:
    """Raderna modellen och utkastet får citera (grundningsgrinden)."""
    rader: list[str] = []
    mobil = (rev.get("pagespeed") or {}).get("mobil") or {}
    if mobil.get("prestanda") is not None:
        rad = f"Google PageSpeed på mobil: prestanda {mobil['prestanda']} av 100"
        if mobil.get("lcp_s") is not None:
            rad += f", huvudinnehållet syns efter {str(mobil['lcp_s']).replace('.', ',')} sekunder"
        rader.append(rad + ".")
    if rev.get("modernitet") is not None:
        era = _LAYOUT_TEXT.get(str(rev.get("layout_era") or ""), "")
        rader.append(
            f"Visuell bedömning av startsidan: modernitet {rev['modernitet']} av 10"
            + (f", {era}" if era else "")
            + (f", designen ser ut att vara från omkring {rev['uppskattat_byggar']}" if rev.get("uppskattat_byggar") else "")
            + "."
        )
    rader += [f"Synlig brist på startsidan: {b}" for b in rev.get("brister") or []]
    return rader


async def revidera(url: str | None, fakta: dict[str, Any]) -> dict[str, Any]:
    """Hela revisionen för en startsida. {} när den är avstängd eller sajten
    saknas. Kastar aldrig."""
    if not url or not aktiv():
        return {}
    mobil, desktop = await asyncio.gather(pagespeed(url, "mobile"), pagespeed(url, "desktop"))
    skarmbild = (desktop or {}).get("skarmbild") or (mobil or {}).get("skarmbild")
    if not skarmbild:
        skarmbild = await skarmbild_via_scrapegraph(url)
    vis = await visuell(url, skarmbild, fakta) if skarmbild else None
    rev: dict[str, Any] = {
        "pagespeed": {
            namn: {k: v for k, v in (ps or {}).items() if k != "skarmbild"}
            for namn, ps in (("mobil", mobil), ("desktop", desktop)) if ps
        },
    }
    if vis:
        rev.update(
            modernitet=vis["modernitet"],
            layout_era=vis.get("layout_era"),
            uppskattat_byggar=vis.get("uppskattat_byggar"),
            brister=vis["top_3_brister"],
            internationell=vis.get("intern_eller_internationell") == "internationell",
            detaljer={k: vis.get(k) for k in (
                "navigering_tydlig", "hero_modern", "typografi_och_luft", "bildkvalitet", "fortroende")},
        )
    rev["rader"] = citerbara_rader(rev)
    return rev


def demo() -> None:
    rev = {"pagespeed": {"mobil": {"prestanda": 38, "lcp_s": 7.8}}, "modernitet": 3, "layout_era": "tabeller",
           "uppskattat_byggar": 2014, "brister": ["Liten text i menyn"]}
    rader = citerbara_rader(rev)
    assert rader[0] == "Google PageSpeed på mobil: prestanda 38 av 100, huvudinnehållet syns efter 7,8 sekunder."
    assert "modernitet 3 av 10, tabellbaserad layout" in rader[1] and "2014" in rader[1]
    assert rader[2] == "Synlig brist på startsidan: Liten text i menyn"
    assert _json_ur('Svar: {"modernitet": 4}') == {"modernitet": 4}
    print("webbrevision: ok")


if __name__ == "__main__":
    demo()
