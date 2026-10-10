"""Organisationsnumret ur bolagets egen webbplats (Sebbe 2026-10-09).

## Varför

Leads som den gamla sökkedjan hittade (regel 11: grounded sökning när
registret ger för få) saknar org.nr. Utan det får ett lead från en
provkörning inte flyttas över till de riktiga (`befordran.saknade_falt`), och
två bolag föll så i "Skicka alla" den 9 oktober.

## Varifrån

Först bolagets EGEN sajt: många bolag skriver "Org.nr 556…" i sidfoten
eller på kontaktsidan. Startsidan och kontakt- och om oss-sidorna läses med
gratis direkthämtning eller cache, aldrig betald ScrapeGraph.

Annars registret: merinfos FÖRETAGSsökning på bolagsnamnet (Sebbes beslut
2026-10-09, se `orgnr_i_registret`). Personsidor används aldrig (Antons
regel 6).

## Vad som godtas

- Bara ett nummer som står UTTRYCKLIGEN som organisationsnummer ("Org.nr",
  "Organisationsnummer", "Orgnr"), inte vilka tio siffror som helst.
- Kontrollsiffran ska stämma (`orgnr.validera_format`).
- Juridisk person: tredje siffran minst 2. En enskild firmas org.nr är
  ägarens personnummer, och ett personnummer hämtas aldrig hit (det är en
  känslig personuppgift, och enskilda firmor kontaktas inte i listorna).
- Står två olika nummer på sajten (koncern, webbyrå i sidfoten) avgörs
  inget: hellre inget nummer än fel bolags.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from .orgnr import OgiltigtOrgnrError, validera_format

logger = logging.getLogger("snajp-support.leads.orgnr_uppslag")

_ORGNR_I_TEXT = re.compile(
    r"(?i)\b(?:org(?:anisations)?\.?\s*-?\s*(?:nr|nummer)|orgnr)\b\.?\s*[:.]?\s*"
    r"(?P<a>\d{6})\s*[-–]?\s*(?P<b>\d{4})\b"
)

#: Sidor som läses, utöver kontaktlänkarna startsidan pekar på.
_SIDOR = ("/kontakt", "/kontakta-oss", "/om-oss", "/om")


def orgnr_i_text(text: str) -> set[str]:
    """Giltiga organisationsnummer för juridiska personer som texten anger
    uttryckligen, som "556824-9022"."""
    hittade: set[str] = set()
    for m in _ORGNR_I_TEXT.finditer(text or ""):
        siffror = m.group("a") + m.group("b")
        if int(siffror[2]) < 2:
            continue  # personnummer (enskild firma): hämtas aldrig
        try:
            tio = validera_format(siffror)
        except OgiltigtOrgnrError:
            continue
        hittade.add(f"{tio[:6]}-{tio[6:]}")
    return hittade


def entydigt(sidor: list[str]) -> str | None:
    """Numret om sajten anger exakt ett, annars None."""
    alla: set[str] = set()
    for text in sidor:
        alla |= orgnr_i_text(text)
    return next(iter(alla)) if len(alla) == 1 else None


# -- Registret (merinfo), när sajten inte anger numret ------------------------
#
# Sebbes beslut 2026-10-09: de flesta småbolag har inget org.nr på startsidan
# eller kontaktsidan (4 av 19 i Snajps lista). Merinfos FÖRETAGSsökning
# (`d=c`; utan den listas privatpersoner först, och sådana används aldrig,
# Antons regel 6) laddar resultaten med JavaScript och hämtas därför i
# webbläsarläge, 2 krediter. Bara bolagsfakta läses: namn, org.nr ur länken
# och orten ur adressraden. Telefonnummer och personer ignoreras.

_TRAFF = re.compile(
    r"^##\s*\[\s*(?P<namn>[^\]]+?)\s*\]\((?P<url>https://www\.merinfo\.se/foretag/[^)\s]+)\)",
    re.MULTILINE,
)
_ORGNR_I_LANK = re.compile(r"-(\d{10})/[\w-]+/?$")
_POSTORT = re.compile(r"\b\d{3} ?\d{2}\s+(?P<ort>[A-Za-zÅÄÖÉåäöé][^\n\[\]]*)")
_BOLAGSFORM = re.compile(r"\b(aktiebolag|ab|handelsbolag|hb|kommanditbolag|kb|ek\.? ?för\.?)\b\.?", re.IGNORECASE)


def _normnamn(namn: str) -> str:
    n = (namn or "").casefold().replace("&", " och ")
    n = _BOLAGSFORM.sub(" ", n)
    n = re.sub(r"[^\wåäöé]+", " ", n)
    return " ".join(n.split())


def tolka_sokresultat(md: str) -> list[dict[str, str | None]]:
    """En post per bolag i merinfos företagssökning: namn, org.nr (None för
    en enskild firma, vars nummer merinfo maskerar) och ort."""
    traffar: list[dict[str, str | None]] = []
    rader = list(_TRAFF.finditer(md or ""))
    for i, m in enumerate(rader):
        slut = rader[i + 1].start() if i + 1 < len(rader) else len(md)
        block = md[m.end():slut]
        nr = _ORGNR_I_LANK.search(m.group("url"))
        ort = _POSTORT.search(block)
        traffar.append(
            {
                "namn": m.group("namn"),
                "orgnr": f"{nr.group(1)[:6]}-{nr.group(1)[6:]}" if nr else None,
                "ort": ort.group("ort").strip() if ort else None,
            }
        )
    return traffar


def valj_traff(traffar: list[dict[str, str | None]], namn: str, ort: str | None) -> str | None:
    """Exakt en träff som bär samma namn (eller börjar med det) och, när
    leadets ort är känd, ligger på den orten. Annars None: hellre inget
    nummer än ett annat bolags."""
    sokt = _normnamn(namn)
    if not sokt:
        return None
    juridiska = [t for t in traffar if t["orgnr"] and orgnr_i_text(f"Org.nr {t['orgnr']}")]
    ortnorm = (ort or "").casefold().strip()

    def pa_orten(t: dict[str, str | None]) -> bool:
        return not ortnorm or ortnorm in (t["ort"] or "").casefold()

    exakta = [t for t in juridiska if _normnamn(t["namn"] or "") == sokt]
    for urval in (exakta, [t for t in juridiska if _normnamn(t["namn"] or "").startswith(sokt + " ")]):
        kandidater = {t["orgnr"] for t in urval if pa_orten(t)}
        if len(kandidater) == 1:
            return next(iter(kandidater))
        if len(kandidater) > 1:
            return None
    # Ett fullständigt firmanamn med bolagsform ("Jollyroom AB") är unikt i
    # registret: en exakt träff gäller även när leadets ort inte är sätets
    # (Elgigantens huvudkontor ligger inte där butiken är). Utan bolagsform
    # ("Eriksson Byggnads") krävs orten.
    if _BOLAGSFORM.search(namn or "") and len({t["orgnr"] for t in exakta}) == 1:
        return exakta[0]["orgnr"]
    return None


async def orgnr_i_registret(namn: str | None, ort: str | None) -> str | None:
    """Org.nr ur merinfos företagssökning, eller None (registret av, inget
    entydigt svar, hämtningen föll). Kastar aldrig."""
    from urllib.parse import quote

    from . import sidhamtning
    from .sources import merinfo

    if not namn or not merinfo.aktiv():
        return None
    try:
        url = f"{merinfo.BAS}/search?d=c&q={quote(namn.strip())}"
        md, _fel, _via = await sidhamtning.hamta(url, fas="bolag", direkt=False, js=True)
        return valj_traff(tolka_sokresultat(md or ""), namn, ort)
    except Exception:  # noqa: BLE001
        logger.exception("Registeruppslaget av org.nr föll för %s", namn)
        return None


async def hitta_orgnr(website: str | None, namn: str | None = None, ort: str | None = None) -> str | None:
    """Org.nr ur bolagets egen sajt, annars ur registret (`namn`, `ort`),
    eller None. Kräver sidhämtningens kontext (`sidhamtning.starta`) för
    cachen och kredittaket. Kastar aldrig."""
    return await orgnr_pa_sajten(website) or await orgnr_i_registret(namn, ort)


async def orgnr_pa_sajten(website: str | None) -> str | None:
    """Org.nr ur bolagets sajt, eller None. Kastar aldrig."""
    from . import sidhamtning
    from .discovery import extrahera_kontaktlankar

    if not website or not str(website).strip():
        return None
    bas = website if "://" in website else "https://" + website
    sidor: list[str] = []
    try:
        start, _fel, _via = await sidhamtning.hamta(bas, fas="webb", direkt=True, betald=False)
        if start:
            sidor.append(start)
            if orgnr_i_text(start):
                return entydigt(sidor)
        lasta = {bas}
        for url in [*extrahera_kontaktlankar(start or "", bas, tak=3), *(urljoin(bas, s) for s in _SIDOR)]:
            if url in lasta:
                continue
            lasta.add(url)
            text, _fel, _via = await sidhamtning.hamta(url, fas="webb", direkt=True, betald=False)
            if text:
                sidor.append(text)
                if orgnr_i_text(text):
                    break
    except Exception:  # noqa: BLE001 — ett uppslag får aldrig fälla anroparen
        logger.exception("Org.nr-uppslaget föll för %s", website)
    return entydigt(sidor)
