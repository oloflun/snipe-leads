"""Förfiltret: fäll kandidater på KÄND data innan de kostar ett researchanrop.

Uppmätt 2026-09-29: källträffarna (JobTech, nyheter) fylldes med bolag på
700 anställda och huvudkontor i Stockholm, som researchen sedan fällde —
hitta först, förkasta sen. Här fälls det som redan går att se på
kandidaten: storlek och ort från källan, uteslutna branscher/domäner i namn
och webbplats, och enskild firma.

Okänt fäller aldrig (samma regel som kvalificeringsgrinden): de flesta
småbolag saknar uppgifterna i källan, och "vet inte" är researchens fråga.

En fälld kandidat blir aldrig ett prospekt (dataminimering) — den hamnar
bara i körningens tratt med namn och skäl.
"""

from __future__ import annotations

import re
from typing import Any

from .geo import _prefix_ur_postnr
from .profil import KOMMUNER

#: Enskild firma: marknadsföringslagen 19 § kräver förhandssamtycke för
#: e-post till fysiska personer, och en enskild näringsidkare ÄR en fysisk
#: person. Orgnr för en enskild firma är ett personnummer — sekelsiffran
#: saknas, men månadssiffran (tredje–fjärde) är 01–12, medan juridiska
#: personer har ≥20 där.
def ar_enskild_firma(orgnr: object) -> bool:
    siffror = "".join(t for t in str(orgnr or "") if t.isdigit())[-10:]
    if len(siffror) != 10:
        return False
    return 1 <= int(siffror[2:4]) <= 12


def _innehaller(text: str, ord_: str) -> bool:
    return bool(ord_) and re.search(rf"\b{re.escape(ord_.casefold())}", text.casefold()) is not None


def forfiltrera(profil: dict[str, Any], kandidat: dict[str, Any], *, exclude_domains: list[str] | None = None) -> str | None:
    """None = gå vidare till research. Annars skälet, på svenska."""
    if ar_enskild_firma(kandidat.get("orgnr")):
        return "Enskild firma — e-post kräver förhandssamtycke (marknadsföringslagen 19 §)."

    antal = kandidat.get("anstallda")
    if isinstance(antal, int) and not isinstance(antal, bool):
        lo, hi = profil.get("anstallda_min"), profil.get("anstallda_max")
        if hi is not None and antal > hi:
            return f"För stort: {antal} anställda enligt källan (högst {hi})."
        if lo is not None and antal < lo:
            return f"För litet: {antal} anställda enligt källan (minst {lo})."

    kommuner = [KOMMUNER[k.casefold()] for k in profil.get("kommuner") or [] if k.casefold() in KOMMUNER]
    if kommuner:
        prefix = _prefix_ur_postnr(kandidat.get("postnr"))
        ort = str(kandidat.get("ort") or "").strip().casefold()
        if prefix is not None and not any(k.innehaller_prefix(prefix) for k in kommuner):
            return f"Utanför målområdet: postnummer {kandidat.get('postnr')}."
        if prefix is None and ort in KOMMUNER and ort not in {k.namn.casefold() for k in kommuner}:
            return f"Utanför målområdet: {kandidat.get('ort')}."

    text = f"{kandidat.get('company_name') or ''} {kandidat.get('website') or ''} {kandidat.get('signal_detalj') or ''}"
    for bransch in profil.get("undvik_branscher") or []:
        if _innehaller(text, bransch):
            return f"Bransch kunden undviker: {bransch}."

    domän = str(kandidat.get("website") or "").lower()
    for d in exclude_domains or []:
        if d and d in domän:
            return f"Domän kunden uteslutit: {d}."
    return None


def demo() -> None:
    profil = {"anstallda_max": 49, "kommuner": ["Göteborg", "Mölndal"], "undvik_branscher": ["bemanning"]}
    assert forfiltrera(profil, {"company_name": "X", "anstallda": 700})
    assert forfiltrera(profil, {"company_name": "X", "postnr": "111 22"})
    assert forfiltrera(profil, {"company_name": "X", "ort": "Partille"})
    assert forfiltrera(profil, {"company_name": "Bemanning Väst AB"})
    assert forfiltrera(profil, {"company_name": "X", "orgnr": "990402-1392"})
    assert forfiltrera(profil, {"company_name": "X", "orgnr": "556824-9022", "postnr": "421 32", "anstallda": 4}) is None
    assert forfiltrera(profil, {"company_name": "Okänd AB"}) is None
    print("forfilter: ok")


if __name__ == "__main__":
    demo()
