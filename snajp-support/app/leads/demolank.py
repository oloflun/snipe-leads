"""Demolänken i utkasten: kundens demo, en spårad länk per tråd, i kod.

Antons beställning 2026-11-15: varje utkast i utkorgen och varje erbjudande,
A eller B, ska bära en länk till demon "ett snäpp ned från resten av
texten", och vi ska kunna se vilka som faktiskt besökt den.

## Formen

Raden står i ett eget stycke efter mejlets sista mening och före
hälsningsfrasen och signaturen:

    … så bokar vi en kostnadsfri genomgång.

    Länk till vår demo, där du kan se hur det fungerar och testa mot ert företag: https://www.snajp.se/prova/k7Hq2xYpQ1c

    Vänliga hälsningar,
    …

KODEN skriver raden, aldrig modellen (samma skäl som signaturen och foten):
en URL i modellens text hade fällts av faktagrinden, och en rad som bara
"brukar" komma med hade gjort mätningen tyst fel.

## Spårningen

Länken är `{PUBLIK_BAS_URL}/prova/<token>`, en token per tråd
(`storage.demolanktoken`, tabellen `ss_demolankar`, migration 116). Next-
routen `app/prova/[token]` loggar ett klick och skickar vidare till kundens
demo; demosidan loggar ett besök vid mottagarens första interaktion. E-post-
skydd (Safe Links, Proofpoint …) klickar på länkar men rör inte sidan, så
"besökt" betyder en människa och "klick" kan vara en skanner. Samma domän som
avsändarens webbplats, ingen tredjepartsspårare: en länk till en okänd
spårningsdomän är en klassisk spamsignal.

## Var valet bor

Kundens demolänk står i erbjudandevalet (`settings.erbjudanden.demo`): en
URL för alla produkter eller en per produkt, samma form som ett villkor.
Utan demolänk: inget block, ingen rad, exakt dagens beteende.
"""

from __future__ import annotations

import re
import secrets
from typing import Any
from urllib.parse import urlparse

URL_MAX = 300
#: Länkvägen i Next (app/prova/[token]/route.ts).
LANKVAG = "/prova/"

RAD = {
    "du": "Länk till vår demo, där du kan se hur det fungerar och testa mot ert företag:",
    "ni": "Länk till vår demo, där ni kan se hur det fungerar och testa mot ert företag:",
    "en": "Here is a link to our demo, where you can see how it works and test it on your company:",
}

#: Hälsningsfrasen sist i brödtexten ("Vänliga hälsningar," eventuellt följd
#: av ett namn): raden går in före den.
_AVSLUT = re.compile(
    r"^[ \t]*(?:(?:med\s+)?(?:vänliga|bästa|varma)\s+hälsningar|hälsningar|mvh|vänligen|"
    r"best\s+regards|kind\s+regards|regards|best\s+wishes|best|cheers)[ \t]*[,!.]?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


#: E-postskydd och förhandsvisningar som klickar på länkar åt mottagaren.
#: Samma lista som SQL-funktionen demolank_klick (migration 116), som dessutom
#: märker klick inom två minuter från utskicket.
_SKANNER_UA = re.compile(
    r"(bot|crawl|spider|preview|scan|safelinks|proofpoint|mimecast|barracuda|"
    r"forcepoint|symantec|trend ?micro|sophos|fortinet|cisco|ironport|"
    r"python|curl|wget|go-http|java/|okhttp|headless|phantom|httpclient|"
    r"microsoft office|outlook-ios|googleimageproxy|yahoo! slurp)",
    re.IGNORECASE,
)


def ser_ut_som_skanner(user_agent: str | None) -> bool:
    return not (user_agent or "").strip() or bool(_SKANNER_UA.search(user_agent or ""))


def ny_token() -> str:
    """Kort och ogissbar nog (≈64 bitar): en gissad token ger bara ett falskt
    klick, aldrig någon annans data, och länken står synlig i mejlet."""
    return secrets.token_urlsafe(8)


def giltig_url(raw: Any) -> str | None:
    """En http(s)-URL med värd, strippad och klippt, eller None. En väg som
    börjar med "/" ("/demo/leads") är en sida på plattformens egen webbplats
    (PUBLIK_BAS_URL): samma inställning gäller då i development och main."""
    text = str(raw or "").strip()
    if not text or len(text) > URL_MAX:
        return None
    if text.startswith("/") and not text.startswith("//") and " " not in text:
        return text
    if not re.match(r"^https?://", text, re.IGNORECASE):
        text = f"https://{text}"
    delar = urlparse(text)
    if delar.scheme not in ("http", "https") or not delar.netloc or " " in text:
        return None
    return text


def normalisera(raw: Any) -> str | dict[str, str] | None:
    """Kundens demolänk tolerant läst: en URL för alla, eller {produkt: URL}."""
    if isinstance(raw, str):
        return giltig_url(raw)
    if isinstance(raw, dict):
        per = {str(p).strip(): u for p, v in raw.items() if str(p).strip() and (u := giltig_url(v))}
        return per or None
    return None


def validera(raw: Any, produkter: list[str]) -> str | dict[str, str] | None:
    """Skrivvägen: kastar ValueError med ett svenskt besked."""
    if raw is None or raw == "" or raw == {}:
        return None
    if isinstance(raw, str):
        url = giltig_url(raw)
        if not url:
            raise ValueError("Demolänken måste vara en webbadress (https://…).")
        return url
    if not isinstance(raw, dict):
        raise ValueError("Demolänken är en webbadress eller en adress per produkt.")
    kanda = {p.strip().casefold() for p in produkter}
    ut: dict[str, str] = {}
    for produkt, varde in raw.items():
        if not str(varde or "").strip():
            continue
        if str(produkt).strip().casefold() not in kanda:
            raise ValueError(f"Demolänken gäller produkten \"{produkt}\", som inte finns bland era produkter.")
        url = giltig_url(varde)
        if not url:
            raise ValueError(f"Demolänken för {produkt} måste vara en webbadress (https://…).")
        ut[str(produkt).strip()] = url
    return ut or None


def demo_for(demo: str | dict[str, str] | None, produkt: str | None) -> str | None:
    """Demolänken för `produkt`. En URL för alla gäller alltid; per produkt
    gäller produktens, annars den första (en demo är bättre än ingen: mejlet
    nämner piloten och demon oavsett produkt)."""
    if isinstance(demo, str):
        return demo
    if isinstance(demo, dict) and demo:
        if produkt:
            nyckel = produkt.strip().casefold()
            traff = next((u for p, u in demo.items() if p.casefold() == nyckel), None)
            if traff:
                return traff
        return next(iter(demo.values()))
    return None


def lank(bas_url: str, token: str) -> str:
    return f"{bas_url.rstrip('/')}{LANKVAG}{token}"


def rad(url: str, *, sprak: str, du: bool) -> str:
    """Raden med länken, i mejlets språk och tilltal."""
    return f"{RAD['en' if sprak == 'en' else ('du' if du else 'ni')]} {url}"


def har_demolank(text: str) -> bool:
    return LANKVAG in (text or "") and bool(re.search(r"/prova/[A-Za-z0-9_-]{6,}", text or ""))


def _bara_former(demo_urls: list[str]) -> re.Pattern[str] | None:
    """Mönstret för en nakna omnämnande av kundens demo i modellens text
    ("snajp.se/demo", "https://www.snajp.se/demo/leads"): värden utan www
    och vägens första led, med valfritt schema, www och undersida."""
    alternativ: set[str] = set()
    for url in demo_urls:
        delar = urlparse(url)
        vard = re.sub(r"^www\.", "", delar.netloc.lower())
        forsta = (delar.path or "/").strip("/").split("/")[0]
        if not vard and forsta:
            # En väg på den egna webbplatsen: vilken domän som helst följd av
            # vägens första led ("snajp.se/demo" i texten, oavsett miljö).
            alternativ.add(rf"[\w-]+(?:\.[\w-]+)+/{re.escape(forsta)}")
            continue
        # Utan väg (demon på startsidan) byts inget: "snajp.se" ensamt är
        # bolagets namn i texten, inte en hänvisning till demon.
        if vard and forsta:
            alternativ.add(f"{re.escape(vard)}/{re.escape(forsta)}")
    if not alternativ:
        return None
    kropp = "|".join(sorted(alternativ, key=len, reverse=True))
    return re.compile(rf"(?:https?://)?(?:www\.)?(?:{kropp})(?:/[\w./-]*)?(?<![.])", re.IGNORECASE)


def utan_bar_demo(text: str, demo_urls: list[str], *, sprak: str) -> str:
    """Byter modellens nakna demoadress mot en hänvisning till länken nedan.

    Villkoren för Snajps pilot säger "titta gärna på demon på snajp.se/demo",
    och den spårade länken står nu i ett eget stycke under: två adresser till
    samma demo, och den nakna hade aldrig räknats."""
    monster = _bara_former(demo_urls)
    if not monster:
        return text
    if sprak == "en":
        text = re.sub(rf"\b(?:at|on)\s+(?:{monster.pattern})", "via the link below", text, flags=re.IGNORECASE)
        return monster.sub("the link below", text)
    text = re.sub(rf"\b(?:på|via)\s+(?:{monster.pattern})", "via länken nedan", text, flags=re.IGNORECASE)
    return monster.sub("länken nedan", text)


def med_demolank(text: str, demorad: str, *, svans_start: int | None = None) -> str:
    """Raden i ett eget stycke efter brödtexten och före hälsningsfrasen.
    Idempotent: bär texten redan en demolänk lämnas den orörd.

    `svans_start` är var kodens svans (signatur, fot) börjar, om den finns
    (`signatur.dela_utkast`); raden hamnar alltid före den."""
    if har_demolank(text):
        return text
    slut = len(text) if svans_start is None else svans_start
    huvud, svans = text[:slut], text[slut:]
    # Hälsningsfrasen bland brödtextens sista tre rader ("Vänliga hälsningar,"
    # eller "Vänliga hälsningar,\nAnton").
    rader = huvud.rstrip().split("\n")
    sista = "\n".join(rader[-3:])
    traffar = list(_AVSLUT.finditer(sista))
    if traffar:
        i = len(huvud.rstrip()) - len(sista) + traffar[-1].start()
        fore, efter = huvud[:i], huvud[i:]
        nytt = f"{fore.rstrip()}\n\n{demorad}\n\n{efter.lstrip()}"
    else:
        nytt = f"{huvud.rstrip()}\n\n{demorad}"
    if svans.strip():
        return f"{nytt.rstrip()}\n\n{svans.lstrip(chr(10))}"
    return nytt


async def lagg_till(
    storage,
    tenant_id: str,
    thread_id: str,
    text: str,
    *,
    sprak: str,
    installningar: dict[str, Any] | None = None,
) -> str:
    """Utkastets text med demolänken, eller oförändrad text när kunden saknar
    demolänk eller den publika adressen saknas. Kastar aldrig: ett utkast
    utan länk är bättre än ett utkast som inte köas."""
    import logging

    from ..agent.leads_research_v2 import las_produkter
    from ..config import get_settings
    from . import erbjudanden
    from .signatur import dela_utkast, normalisera as normalisera_signatur
    from .stilkontroll import namngiven

    try:
        bas_url = get_settings().publik_bas_url
        if not bas_url or not thread_id or har_demolank(text):
            return text
        if installningar is None:
            installningar = await storage.get_agent_settings(tenant_id, agent_type="leads")
        demo = normalisera((installningar.get("erbjudanden") or {}).get("demo"))
        if not demo:
            return text
        sig = normalisera_signatur(installningar.get("signatur"))
        brodtext, _svans = dela_utkast(text, sig)
        produkt = erbjudanden.produkt_nu(None, brodtext, las_produkter(installningar))
        mal = demo_for(demo, (produkt or {}).get("namn"))
        if not mal:
            return text
        alla = [demo] if isinstance(demo, str) else list(demo.values())
        renad = utan_bar_demo(brodtext, alla, sprak=sprak)
        if renad != brodtext:
            text = renad + text[len(brodtext):]
            brodtext = renad
        token = await storage.demolanktoken(tenant_id, thread_id=thread_id, mal_url=mal)
        demorad = rad(lank(bas_url, token), sprak=sprak, du=sprak != "en" and namngiven(brodtext))
        return med_demolank(text, demorad, svans_start=len(brodtext) if len(brodtext) < len(text.rstrip()) else None)
    except Exception:  # noqa: BLE001 — se docstringen
        logging.getLogger("snajp-support.leads.demolank").exception(
            "Demolänken kunde inte läggas på i tråd %s; utkastet köas utan.", thread_id
        )
        return text
