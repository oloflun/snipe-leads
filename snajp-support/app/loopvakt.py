"""Loopvakten: loggar VAR händelseloopen står still, medan den står still.

API:t och leadsarbetarna delar en process och en händelseloop. När ett
leadsjobb gör CPU-arbete utan att släppa loopen (en regex, en stor
json.dumps, HTML-tolkning) väntar varje API-anrop: Att göra, flikbytena,
allt. Uppmätt 2026-10-10 under en körning: /health/live svarade på 110–470 ms
mot webbens jämna 120–140.

Att hitta stoppet i efterhand är svårt — loggen tystnar bara (se
snipe-korningar-skala 2026-10-09, där det tog ett handbyggt skript). Vakten
gör det löpande: loopen slår ett pulsslag var 50:e ms, en tråd utanför loopen
tittar på pulsen, och står den still längre än tröskeln loggas loopens stack
JUST DÅ. Raden som håller loopen är den som syns.

Kostnaden är ett timeranrop var 50:e ms och en sovande tråd. En regex eller
ett C-anrop som håller GIL:en hela vägen syns inte mitt i stoppet — tråden
får inte köra — men längden loggas när loopen släpper, med stacken därifrån.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
import traceback

logger = logging.getLogger("snajp-support.loopvakt")

PULS_S = 0.05
#: Högst en logg per så många sekunder, så att ett segt jobb inte dränker loggen.
LOGG_MELLANRUM_S = 5.0


def starta(troskel_ms: int) -> None:
    """Startar vakten för den körande loopen. 0 eller mindre = av."""
    if troskel_ms <= 0:
        return
    loop = asyncio.get_running_loop()
    loop_trad = threading.get_ident()
    troskel = troskel_ms / 1000
    puls = {"t": time.monotonic()}

    def slag() -> None:
        puls["t"] = time.monotonic()
        loop.call_later(PULS_S, slag)

    loop.call_soon(slag)

    def vakt() -> None:
        senast_loggad = 0.0
        loggad_puls = None
        while not loop.is_closed():
            time.sleep(PULS_S)
            nu = time.monotonic()
            stilla = nu - puls["t"] - PULS_S
            if stilla < troskel or loggad_puls == puls["t"] or nu - senast_loggad < LOGG_MELLANRUM_S:
                continue
            ram = sys._current_frames().get(loop_trad)
            stack = "".join(traceback.format_stack(ram, limit=14)) if ram else "(ingen stack)"
            logger.warning("Händelseloopen står still sedan %.0f ms. Loopens stack nu:\n%s", stilla * 1000, stack)
            loggad_puls = puls["t"]
            senast_loggad = nu

    threading.Thread(target=vakt, name="loopvakt", daemon=True).start()
