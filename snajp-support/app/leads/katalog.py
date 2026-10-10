"""Företagskatalogen (hitta.se) som kontaktkälla, sökt på org.nr.

Anton 2026-10-10: "det finns ALLTID kontaktinformation, det gäller bara att
leta tillräckligt". Två av hans exempel som blev ej kvalificerade hade
uppgifterna öppet i katalogen: Norrtech i Skellefteå AB (ingen telefon hos
merinfo, men hitta har växeln och en adress på norrtech.se) och Örnbergs
Plåtslageri (070-numret, utan VD i registret).

hitta.se svarar på en vanlig förfrågan (ingen ScrapeGraph-kredit) och bär
bolagets uppgifter strukturerat i sidans __NEXT_DATA__. Sökningen görs på
org.nr, så träffen är samma juridiska person som i registret, oavsett vilket
varumärke bolaget använder.

Gemini med Google-sökning och URL-kontext provades först (2026-10-10, Vertex
EU): 2.5-flash bytte till ett annat bolag när den inte hittade det sökta,
2.5-pro och 3.6-flash (bara global ändpunkt) sökte inte alls. Se
docs/BESLUT.md.

Uppgifterna är bolagsnivå (bolagets publicerade nummer och e-post), aldrig
personsidor (regel 6)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import quote

logger = logging.getLogger("snajp-support.leads.katalog")

_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def tolka_hitta(html: str) -> dict[str, Any] | None:
    """Första bolagsträffen i hitta.se:s sökresultat: {namn, telefon, epost,
    url}, eller None. Ren funktion (testas mot sparad sida)."""
    m = _NEXT_DATA.search(html or "")
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        bolag = data["props"]["pageProps"]["result"]["companies"]
    except (ValueError, KeyError, TypeError):
        return None
    if not bolag:
        return None
    b = bolag[0]
    attribut = {a.get("name"): a.get("value") for a in b.get("attribute") or [] if isinstance(a, dict)}
    telefon = next((p.get("displayAs") for p in b.get("phone") or [] if p.get("displayAs")), None)
    epost = str(attribut.get("email") or "").strip().lower() or None
    if not (telefon or epost):
        return None
    return {"namn": b.get("displayName"), "telefon": telefon, "epost": epost}


async def hitta(orgnr: str | None) -> dict[str, Any] | None:
    """Katalogens uppgifter för ett org.nr, eller None. Kastar aldrig.

    Egen hämtning, inte research_tools._hamta_direkt: den gör om sidan till
    text, och uppgifterna står i sidans JSON."""
    import httpx

    from ..agent.research_tools import _DIREKT_HEADERS
    from ..tls import ssl_kontext
    from . import sidhamtning

    siffror = re.sub(r"\D", "", str(orgnr or ""))[-10:]
    # Testsviten har direkthämtningen av: ingen förfrågan ut därifrån.
    if len(siffror) != 10 or not sidhamtning._direkt_forst():
        return None
    url = f"https://www.hitta.se/{quote('sök')}?vad={siffror}"
    try:
        async with httpx.AsyncClient(
            verify=ssl_kontext(), timeout=httpx.Timeout(15.0), headers=_DIREKT_HEADERS
        ) as client:
            svar = await client.get(url)
    except httpx.HTTPError as fel:
        logger.info("Katalogen svarade inte för %s: %s", siffror, type(fel).__name__)
        return None
    if svar.status_code != 200:
        logger.info("Katalogen svarade %s för %s", svar.status_code, siffror)
        return None
    return tolka_hitta(svar.text)


async def berika(k: dict[str, Any]) -> dict[str, Any]:
    """Kandidaten med katalogens uppgifter där registret saknar dem.

    * `_epost`: bolagets e-post. Registrets e-post går före. Den ger också
      webbplatsen via domänen (merinfo._webbplats steg 2): Norrtech fick
      norrtech.se så.
    * `_telefon` + `_telefon_katalog`: numret bolaget publicerar i katalogen.
      Det räknas som bolagets publicerade nummer, som sajtens (regel 12, 15),
      och kräver därför ingen VD i registret (merinfo.fordela).

    Enskilda firmor slås inte upp: de går aldrig till ringlistan (NIX)."""
    from .sources.merinfo import ar_enskild

    if ar_enskild(k) or not k.get("orgnr"):
        return k
    if k.get("_epost") and k.get("_telefon") and k.get("vd_namn"):
        return k
    h = await hitta(k.get("orgnr"))
    if not h:
        return k
    ut = {**k, "_katalog": "hitta.se"}
    if h["epost"] and not k.get("_epost"):
        ut["_epost"] = h["epost"]
    if h["telefon"]:
        # Katalogens nummer går före registrets: det är det bolaget själv
        # publicerar, och flaggan gäller bara det numret.
        ut["_telefon"] = h["telefon"]
        ut["_telefon_katalog"] = True
    return ut
