"""Medarbetarens svar ut i kundens kanal (sömlös överlämning, snipe-1fl).

`overlamning.medarbetarsvar` sparar svaret i ärendets tråd. Webbchatten
hämtar det själv (widgetpollning), men en kund i WhatsApp eller Teams har
ingen widget. Svaret måste SKICKAS dit. Det gör den här modulen, via samma
adapter och samma kontaktadress som agentens svar.

Anropas efter att svaret sparats, aldrig i stället för det: databasen är
sanningen om vad medarbetaren skrev, och ett leveransfel ska synas för
medarbetaren ("sparat men inte levererat: 24-timmarsfönstret har stängt"),
inte radera svaret.
"""

from __future__ import annotations

from typing import Any

from . import ADAPTRAR, lagring
from .bas import KanalFel


async def leverera(storage: Any, tenant_id: str, *, customer_id: str, kanal: str | None, text: str) -> bool:
    """Skickar `text` till kunden i `kanal`.

    Returnerar False när kanalen inte är en extern kanal (web, email): där
    finns inget att leverera. Kastar KanalFel när leveransen misslyckas.
    """
    adapter = ADAPTRAR.get(kanal or "")
    if adapter is None:
        return False
    traff = await lagring.senaste_kontakt(storage, tenant_id, customer_id, kanal=adapter.kanal)
    if traff is None:
        raise KanalFel(
            f"Kunden har ingen aktiv {adapter.kanal}-anslutning att svara i. "
            "Är kanalen avstängd eller borttagen?"
        )
    kontakt, anslutning = traff
    try:
        hemligheter = lagring.dekryptera_hemligheter(anslutning)
    except Exception as fel:  # noqa: BLE001 — nyckelproblem blir ett begripligt fel
        raise KanalFel(f"Kanalens nycklar gick inte att läsa: {fel}") from fel
    await adapter.skicka(
        anslutning,
        hemligheter,
        mottagare=kontakt["extern_anvandare"],
        adress=kontakt.get("adress") or {},
        text=text,
    )
    return True
