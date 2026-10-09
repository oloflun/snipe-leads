"""Organisationsnumret ur bolagets egen webbplats (Sebbe 2026-10-09).

## Varför

Leads som den gamla sökkedjan hittade (regel 11: grounded sökning när
registret ger för få) saknar org.nr. Utan det får ett lead från en
provkörning inte flyttas över till de riktiga (`befordran.saknade_falt`), och
två bolag föll så i "Skicka alla" den 9 oktober.

## Varifrån

Bolagets EGEN sajt: svenska bolag skriver nästan alltid "Org.nr 556…" i
sidfoten eller på kontaktsidan. Det är bolagets egen publicerade uppgift, inte
ett register (merinfo skrapas inte för det här, och personsidor används
aldrig, Antons regel 6). Startsidan och kontakt- och om oss-sidorna läses
genom sidhämtningen med gratis direkthämtning eller cache, aldrig betald
ScrapeGraph.

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


async def hitta_orgnr(website: str | None) -> str | None:
    """Org.nr ur bolagets sajt, eller None. Kräver sidhämtningens kontext
    (`sidhamtning.starta`) för cachen. Kastar aldrig."""
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
