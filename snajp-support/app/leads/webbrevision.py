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
from urllib.parse import urlsplit

import httpx
from ..tls import ssl_kontext

logger = logging.getLogger("snajp-support.leads.webbrevision")

PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PSI_TIMEOUT = httpx.Timeout(90.0, connect=10.0)

_LAYOUT_TEXT = {
    "tabeller": "tabellbaserad layout",
    "tidig_responsiv": "tidig responsiv design",
    "modern": "modern layout",
}

#: Antons facit 2026-10-08 (57 sajter) har fyra nivåer och inget gränsfall.
#: Gränserna på modellens tiogradiga skala; `webbniva` är den enda som läser dem.
AKUT_HOGST = 2
DALIG_HOGST = 5
BRA_HOGST = 8
NIVAER = ("akut", "dalig", "bra", "mycket_bra")

#: Samtyckescookies som säger "besökaren har redan nekat" hos de vanligaste
#: plattformarna. Utan dem täckte rutan halva skärmbilden på ungefär var
#: fjärde sajt i facit 2026-10-08, och bedömningen dömde rutan i stället för
#: sajten. Prövat samma dag: rutan försvann på 5 av 5 (Cookiebot, Complianz,
#: Cookie Information). Neka är det integritetsvänliga svaret.
SAMTYCKE = {
    "CookieConsent": "{stamp:%27-1%27%2Cnecessary:true%2Cpreferences:false%2Cstatistics:false%2C"
                     "marketing:false%2Cmethod:%27explicit%27%2Cver:1%2Cregion:%27se%27}",
    "cmplz_banner-status": "dismissed",
    "cmplz_functional": "allow",
    "cmplz_marketing": "deny",
    "cmplz_statistics": "deny",
    "cmplz_preferences": "deny",
    "CookieInformationConsent": json.dumps({
        "consents_approved": ["cookie_cat_necessary"],
        "consents_denied": ["cookie_cat_functional", "cookie_cat_statistic", "cookie_cat_marketing",
                            "cookie_cat_unclassified"],
    }),
    "OptanonAlertBoxClosed": "2026-10-08T00:00:00.000Z",
    "cookieyes-consent": "consent:no,action:yes,necessary:yes,functional:no,analytics:no,"
                         "performance:no,advertisement:no",
    "moove_gdpr_popup": json.dumps({"strict": "1", "thirdparty": "0", "advanced": "0"}),
    "cookie_notice_accepted": "false",
}

#: Kataloger och plattformar som kan vara ett bolags ENDA webbnärvaro.
#: Facit 2026-10-08: VM Måleris sida på thingsreview.com är deras faktiska
#: sida, och "väldigt dålig, sådana ska absolut kontaktas" (Anton). En sådan
#: närvaro kan aldrig bli bättre än dålig: bolaget har ingen egen sajt.
KATALOGDOMANER = (
    "thingsreview.com", "hitta.se", "eniro.se", "allabolag.se", "merinfo.se", "proff.se", "ratsit.se",
    "121.nu", "facebook.com", "instagram.com", "linkedin.com", "foretagsfakta.se", "reco.se",
)


def _nu() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def startsida(url: str | None) -> str | None:
    """Sajtens startsida. Facit 2026-10-08 hade sex undersidor (`/kopa`,
    `/om-oss` ...) och Carlén dömdes på en tom lagersida. En katalogsida är
    bolagets sida och behåller sin sökväg."""
    if not url:
        return None
    if "://" not in url:
        url = f"https://{url}"
    if ar_katalog(url):
        return url
    delar = urlsplit(url)
    return f"{delar.scheme}://{delar.netloc}/"


def doman(url: str | None) -> str:
    """Värdnamnet utan www., gemener. Nyckeln i webbpoolen."""
    if not url:
        return ""
    host = urlsplit(url if "://" in url else f"https://{url}").hostname or ""
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def ar_katalog(url: str | None) -> bool:
    d = doman(url)
    return any(d == k or d.endswith("." + k) for k in KATALOGDOMANER)


def webbniva(rev: dict[str, Any] | None) -> str:
    """Revisionens nivå: akut, dalig, bra, mycket_bra eller okand.

    Akut avgörs i kod utan bild: ingen sajt, platshållare (parkerad, 404,
    fillistning, under konstruktion) eller en sajt som inte svarar ens på
    andra försöket. En katalogsida stannar på dålig, aldrig bättre."""
    if not rev:
        return "okand"
    if rev.get("saknas") or rev.get("platshallare") or rev.get("svarar_inte"):
        return "akut"
    m = rev.get("modernitet")
    if rev.get("katalog") and (rev.get("skymd") or not isinstance(m, (int, float))):
        return "dalig"  # en katalogsida är aldrig bättre, vad bilden än visar
    if rev.get("skymd") or not isinstance(m, (int, float)):
        return "okand"
    niva = "akut" if m <= AKUT_HOGST else "dalig" if m <= DALIG_HOGST else "bra" if m <= BRA_HOGST else "mycket_bra"
    if rev.get("katalog") and niva in ("bra", "mycket_bra"):
        return "dalig"
    return niva


VISIONPROMPT = """You audit the website of a small Swedish company or organisation for a web \
design agency that sells new websites. Judge only what you can see in the screenshot plus the \
measured facts. The one question that matters: would the owner immediately SEE that a new \
website is a clear upgrade? If yes, the site is dated or poor, however well it works.

Ignore cookie banners, newsletter pop-ups, chat bubbles and language prompts: judge the page \
BEHIND them. Set "skymd" to true only if an overlay hides most of the page so you cannot judge it.

Return ONLY a JSON object with these keys:
- navigering_tydlig: true/false — is there a clear, visible navigation menu?
- hero_modern: true/false — does the top section look current (large own imagery or strong \
typography, clear message, call to action)?
- layout_era: "tabeller" | "tidig_responsiv" | "modern"
- typografi_och_luft: "bra" | "medel" | "dalig" — font sizes, hierarchy, whitespace
- bildkvalitet: "bra" | "medel" | "dalig"
- fortroende: "bra" | "medel" | "dalig" — contact details, references, professional finish
- uppskattat_byggar: integer year the design most likely dates from, or null
- modernitet: integer 1-10
- skymd: true/false
- top_3_brister: up to 3 short, concrete, VISIBLE design flaws written in Swedish; [] if none \
worth raising with the owner
- intern_eller_internationell: "lokal" | "internationell" | "okand" — "internationell" if the site \
presents an international group, offices in several countries, or is English-only

Signs of a DATED or POOR site (two or more → modernitet 3-5):
fixed-width or boxed layout with background visible at the sides; text starts at the top with no \
large image; small or justified body text; stock photos, clip art or drawings instead of the \
company's own photos; visible defects (duplicate logo, image not loaded, empty bands, misaligned \
elements, overlapping text); a default theme with no identity of its own (plain WordPress, \
Bootstrap, Wix or shop theme); clutter of badges, banners or sliders; dated typefaces (Times, \
default Arial, thin all-caps serif).
Signs of a GOOD site (modernitet 6-8): a large full-width top image or video with the company's \
own photos, a clear headline and button, generous and consistent spacing, a deliberate typeface, \
a modern menu. A site built on a theme is still GOOD when it looks like this.

Calibration for modernitet:
1-2 = broken or not a real site: an error page, a placeholder, unstyled HTML, a file listing, only \
a logo and a contact line, or a third-party directory page as the company's only presence.
3-5 = dated (around 2005-2017) or generic and plain: a new site would be a clear upgrade.
6-8 = current and professional: the owner would not see a reason to replace it.
9-10 = agency-grade work with a distinct visual identity, custom type or illustration, motion.
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
        async with httpx.AsyncClient(verify=ssl_kontext(), timeout=PSI_TIMEOUT) as client:
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


#: Krediter per lyckad skärmbild, uppmätt 2026-10-08 mot kreditsaldot:
#: JS-läge med väntan och cookies 2, med stealth 7. Ett misslyckat anrop
#: kostar ingenting. Stealth används därför bara som andra försök (Nimbus
#: visade annars en ruta om "gammal webbläsare" eller fallerade).
SKARMBILD_KREDITER = 2
STEALTH_KREDITER = 7


def _skarmbild_ur_svar(svar: Any) -> Any:
    if getattr(svar, "status", None) != "success":
        return None
    return ((svar.data.results or {}).get("screenshot") or {}).get("data")


async def skarmbild_via_scrapegraph(url: str, *, bara_stealth: bool = False) -> str | None:
    """Skärmbilden, förstahandskällan sedan 2026-10-08: en riktig webbläsare
    (JS, 2,5 s väntan) med samtyckescookies som håller cookierutan borta.
    PageSpeeds bild kan inte bära cookies, och dess nyckellösa kvot är ändå
    slut. Räknas mot körningens kredittak. Kastar aldrig."""
    import base64

    from ..config import get_settings
    from . import sidhamtning

    nyckel = get_settings().scrapegraphai_api_key
    kontext = sidhamtning.aktuell()

    def rymms(krediter: int) -> bool:
        return not kontext or kontext.tak - kontext.totalt >= krediter

    if not nyckel or not rymms(SKARMBILD_KREDITER):
        return None
    data = None
    try:
        from scrapegraph_py import FetchConfig, ScrapeGraphAI, ScreenshotFormatConfig

        client = ScrapeGraphAI(api_key=nyckel)
        forsok = ((True, STEALTH_KREDITER),) if bara_stealth else ((False, SKARMBILD_KREDITER), (True, STEALTH_KREDITER))
        for stealth, krediter in forsok:
            if not rymms(krediter):
                break
            svar = await asyncio.wait_for(
                asyncio.to_thread(
                    client.scrape, url,
                    formats=[ScreenshotFormatConfig(width=1440, height=900)],
                    fetch_config=FetchConfig(mode="js", stealth=stealth, wait=2500, cookies=SAMTYCKE),
                ),
                timeout=90,
            )
            data = _skarmbild_ur_svar(svar)
            if data:
                if kontext:
                    kontext.anrop["skarmbild"] = kontext.anrop.get("skarmbild", 0) + krediter
                break
    except Exception as fel:  # noqa: BLE001
        logger.info("Skärmbilden via ScrapeGraph för %s föll: %s", url, type(fel).__name__)
        return None
    bild = _som_data_url(data)
    lank = data.get("url") if isinstance(data, dict) else data
    if bild is None and isinstance(lank, str) and lank.startswith("http"):
        try:
            async with httpx.AsyncClient(verify=ssl_kontext(), timeout=30) as client:
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
    if rev.get("platshallare"):
        rader.append(f"Webbplatsen är ingen riktig sajt: {rev['platshallare']}.")
    if rev.get("katalog"):
        rader.append("Bolagets enda webbnärvaro är en sida i en katalog, ingen egen webbplats.")
    return rader


async def revidera(url: str | None, fakta: dict[str, Any]) -> dict[str, Any]:
    """Hela revisionen för en startsida. {} när den är avstängd eller sajten
    saknas. Kastar aldrig."""
    if not url or not aktiv():
        return {}
    url = startsida(fakta.get("url") or url) or url
    # En sajt som är trasig enligt mätningen kostar ingen skärmbild: den är
    # akut redan (facit 2026-10-08: 404 hos Netlify och Wix, Bohlin svarar inte).
    status = fakta.get("http_status")
    if fakta.get("platshallare") or fakta.get("svarar_inte") or status in (404, 410) or (status or 0) >= 500:
        rev: dict[str, Any] = {
            "platshallare": fakta.get("platshallare") or (f"felsida ({status})" if status else None),
            "svarar_inte": bool(fakta.get("svarar_inte")),
        }
        rev["webbniva"] = webbniva(rev)
        rev["bedomd"] = _nu()
        rev["rader"] = citerbara_rader(rev)
        return rev
    # PageSpeed bara på mobil och bara för siffrorna (säljargumentet); bilden
    # kommer från ScrapeGraph, med PageSpeeds som reserv.
    mobil, skarmbild = await asyncio.gather(pagespeed(url, "mobile"), skarmbild_via_scrapegraph(url))
    skarmbild = skarmbild or (mobil or {}).get("skarmbild")
    vis = await visuell(url, skarmbild, fakta) if skarmbild else None
    if skarmbild and vis is None:
        # Ett tomt eller trasigt modellsvar (Anna Åberg, kalibreringen 2026-10-08).
        vis = await visuell(url, skarmbild, fakta)
    if vis and vis.get("skymd") is True:
        # En ruta som paketet inte når (bot-kontroll, TCF-samtycke, "gammal
        # webbläsare"): ett andra försök med stealth, 7 krediter.
        andra = await skarmbild_via_scrapegraph(url, bara_stealth=True)
        vis2 = await visuell(url, andra, fakta) if andra else None
        if vis2 and vis2.get("skymd") is not True:
            vis = vis2
    rev = {"pagespeed": {"mobil": {k: v for k, v in mobil.items() if k != "skarmbild"}} if mobil else {}}
    if vis:
        rev.update(
            modernitet=vis["modernitet"],
            layout_era=vis.get("layout_era"),
            uppskattat_byggar=vis.get("uppskattat_byggar"),
            brister=vis["top_3_brister"],
            internationell=vis.get("intern_eller_internationell") == "internationell",
            skymd=vis.get("skymd") is True,
            detaljer={k: vis.get(k) for k in (
                "navigering_tydlig", "hero_modern", "typografi_och_luft", "bildkvalitet", "fortroende")},
        )
    if ar_katalog(url):
        rev["katalog"] = True
    rev["webbniva"] = webbniva(rev)
    rev["bedomd"] = _nu()
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
    assert [webbniva({"modernitet": m}) for m in (2, 3, 5, 6, 8, 9)] == [
        "akut", "dalig", "dalig", "bra", "bra", "mycket_bra"]
    assert webbniva({"modernitet": 8, "katalog": True}) == "dalig"
    assert webbniva({"modernitet": 8, "skymd": True}) == "okand"
    assert webbniva({"katalog": True}) == "dalig"
    assert webbniva({"svarar_inte": True}) == webbniva({"saknas": True}) == "akut"
    assert startsida("https://www.carlenbil.se/kopa") == "https://www.carlenbil.se/"
    assert startsida("thingsreview.com/generic/vm-maleri") == "https://thingsreview.com/generic/vm-maleri"
    assert doman("https://WWW.Pectus.se/x") == "pectus.se"
    print("webbrevision: ok")


if __name__ == "__main__":
    demo()
