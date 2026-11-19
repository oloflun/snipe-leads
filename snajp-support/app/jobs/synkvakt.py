"""Synkvakten: larmar när synken main → development har stått still, eller
när senaste försöket inte lyckades helt (hoppade över rader, avbröts, föll).

## Varför den finns

Synken (scripts/railway_synk.py) skriver sitt utfall i developments
`mirror_meta`, men ingen tittar där av sig själv. 2026-11-10–16 stod synken
röd i sex dagar utan att någon såg det (docs/BESLUT.md). Synkflytt-planen
§ 3 Insyn och runbookens steg 11: api:t i development loggar ett fel när
senaste lyckade synk är äldre än 60 minuter, högst en gång i timmen.

## Skydden

* Bara i development: spegelmarkören ska säga `environment = 'development'`.
  Main har ingen markör (spegel_info() är None) och larmar aldrig.
* Billig: databasen tittas på högst var femte minut (KONTROLL_SEKUNDER), och
  frågan är samma spegel_info() som schemaläggaren redan ställer.
* Får aldrig fälla loopen den hänger i (leads-städaren, app/jobs/stadare.py):
  varje fel loggas som varning och sväljs.
* Ingen persondata i loggraden: bara åldern i minuter och synkens eget
  utfall, som synken redan håller fri från radvärden (skriv_utfall).

Samma ålder och gräns visar panelen Flytta till main via
GET /api/admin/flytt/status (synk_alder_min, synk_forsenad).
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("snajp-support.synkvakt")

#: Äldre än så här (minuter sedan senaste lyckade synk) är synken försenad.
GRANS_MINUTER = 60
#: Larmet loggas högst så här ofta per process.
LARM_SEKUNDER = 3600
#: Databasen tittas på högst så här ofta per process.
KONTROLL_SEKUNDER = 300

#: Monotona tider för senaste kontroll och senaste larm i den här processen.
_tillstand: dict[str, float] = {"kontroll": float("-inf"), "larm": float("-inf")}


def nollstall() -> None:
    """För testerna: glöm senaste kontroll och larm."""
    _tillstand["kontroll"] = float("-inf")
    _tillstand["larm"] = float("-inf")


def _tid(varde: Any) -> datetime | None:
    if isinstance(varde, datetime):
        t = varde
    elif isinstance(varde, str) and varde:
        try:
            t = datetime.fromisoformat(varde)
        except ValueError:
            return None
    else:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def synk_alder_min(spegel: dict[str, Any] | None, *, nu: datetime | None = None) -> int | None:
    """Hela minuter sedan senaste lyckade synk (`synkad_at`). None när det
    inte går att veta: ingen spegel, eller en spegel som aldrig synkats."""
    if not spegel:
        return None
    synkad = _tid(spegel.get("synkad_at"))
    if synkad is None:
        return None
    sekunder = ((nu or datetime.now(timezone.utc)) - synkad).total_seconds()
    return max(int(sekunder // 60), 0)


def synk_forsenad(alder_min: int | None) -> bool:
    """Försenad = känd ålder över gränsen. Okänd ålder larmar inte."""
    return alder_min is not None and alder_min > GRANS_MINUTER


def synk_avvikande_utfall(spegel: dict[str, Any] | None) -> str | None:
    """Senaste försökets utfall när det inte var helt lyckat, annars None.

    Synken sätter `synkad_at` även när enskilda rader hoppats över (de övriga
    är skrivna), så åldern ensam håller vakten tyst om samma rader faller vid
    varje körning (Codex runda 9). Allt utom "ok" (och "hoppade:0", som
    panelen räknar som lyckat) är en avvikelse. Inget utfall alls är okänt och
    larmar inte, precis som en okänd ålder."""
    if not spegel:
        return None
    utfall = spegel.get("senaste_utfall")
    if not isinstance(utfall, str) or not utfall.strip():
        return None
    utfall = utfall.strip()
    return None if utfall in ("ok", "hoppade:0") else utfall


async def vakta(
    storage: Any,
    *,
    klocka: Callable[[], float] = time.monotonic,
    nu: datetime | None = None,
) -> bool:
    """Ett varv. Returnerar True om ett larm loggades. Kastar aldrig (utom
    CancelledError, så att nedstängningen fungerar)."""
    try:
        nu_mono = klocka()
        if nu_mono - _tillstand["kontroll"] < KONTROLL_SEKUNDER:
            return False
        _tillstand["kontroll"] = nu_mono
        spegel = await storage.spegel_info()
        if not spegel or spegel.get("environment") != "development":
            return False
        alder = synk_alder_min(spegel, nu=nu)
        forsenad = synk_forsenad(alder)
        avvikelse = synk_avvikande_utfall(spegel)
        if not forsenad and avvikelse is None:
            return False
        if nu_mono - _tillstand["larm"] < LARM_SEKUNDER:
            return False
        _tillstand["larm"] = nu_mono
        utfall = str(spegel.get("senaste_utfall") or "okänt")[:200]
        if forsenad:
            logger.error(
                "Synken main → development är försenad: senaste lyckade synk för %s min sedan "
                "(gräns %s min). Senaste utfall: %s",
                alder,
                GRANS_MINUTER,
                utfall,
            )
        else:
            logger.error(
                "Synken main → development lyckades inte helt i senaste försöket: %s "
                "(senaste synk för %s min sedan). Rader som hoppas över i varje körning "
                "skiljer main och development åt tills de rättas.",
                utfall,
                "okänt antal" if alder is None else alder,
            )
        return True
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 — vakten får aldrig fälla loopen den hänger i
        logger.warning("Synkvakten kunde inte läsa spegelns status; försöker igen nästa varv.")
        return False
