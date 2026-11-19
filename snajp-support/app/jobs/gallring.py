"""Gallringen: raderar kunddata äldre än kundens beslutade period, en gång per dygn.

## Varför den finns

Integritetspolicyn lovar att uppgifter sparas i 24 månader från den senaste
behandlingen och att gallringen är automatiserad och loggas (GDPR art. 5.1 e).
Mekanismen är databasfunktionen `gallra_alla` (migration 119); den här modulen
är bara klockan som anropar den, och larmet när något inte stämmer.

## Skydden, och var de sitter

* AV som standard (`GALLRING_AKTIV`). Ägaren slår på den i main.
* Kunder utan beslutad policy gallras aldrig — det avgör databasen.
* Högst en gång per svenskt dygn, även med flera api-processer: dygnsspärren
  är en rad i `ss_gallringskorning`, skriven i samma transaktion som
  raderingen. Loopen tittar en gång i timmen och kör tidigast `GALLRING_TIMME`.
* Tak per kund (`GALLRING_TAK`): är urvalet större görs ingenting hos kunden,
  och plattformsadmin larmas (platform_events + prioriterat mejl).
* I en spegel bara det synken inte för över (migration 133). Development får
  main:s raderingar genom synken för de synkade tabellerna; resten
  (genererade mejl, kontakter, feedbacktext, händelser, sidcache …) gallrar
  spegeln själv med samma policy. Det avgör databasfunktionen, inte den här
  modulen. Fram till 2026-11-19 gjorde spegeln ingenting alls, och rader
  utanför synken låg kvar för alltid (Codex-granskningen, runda 3).
* Får aldrig krascha tjänsten: varje fel loggas och loopen fortsätter, samma
  mönster som trial-påminnaren.

## Insyn

Varje körning och kund står i `ss_gallringslogg`; plattformsadmin läser den
via `GET /api/admin/gallring` (app/api/admin_gallring.py).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..config import get_settings

logger = logging.getLogger("snajp-support.gallring")

_SVERIGE = ZoneInfo("Europe/Stockholm")


async def _larma(storage: Any, kund: dict[str, Any], *, tak: int) -> None:
    """Taket nått eller kunden föll: händelselogg och prioriterat mejl. Kastar aldrig."""
    tenant_id = str(kund.get("tenant_id") or "")
    if kund.get("status") == "tak_nadd":
        rubrik = "Gallringen stannade vid taket"
        vad = (
            f"Gallringen skulle ha ändrat {kund.get('totalt')} rader hos kunden, "
            f"fler än taket {tak}. Ingenting ändrades hos kunden."
        )
        varfor = (
            "Antingen är policyvärdet fel, eller så är det kundens första gallring "
            "med lång historik. Kontrollera ss_gallringspolicy och torrkör "
            "scripts/gallra.py för kunden innan den körs skarpt."
        )
    else:
        rubrik = "Gallringen föll för en kund"
        vad = f"Gallringen föll: {str(kund.get('fel') or '')[:300]}"
        varfor = "Kundens ändringar rullades tillbaka; övriga kunder gallrades."
    try:
        from ..api.events import log_event

        await log_event(
            storage,
            level="error",
            source="gallring",
            message=rubrik,
            tenant_id=tenant_id or None,
            detail={"status": kund.get("status"), "totalt": kund.get("totalt"),
                    "tak": tak, "antal": kund.get("antal"), "fel": kund.get("fel")},
        )
    except Exception:  # noqa: BLE001 — larmet får aldrig skugga körningen
        logger.warning("Kunde inte skriva gallringslarmet till platform_events.")
    try:
        from ..notifications.prioriterat_mejl import skicka_prioriterat

        await skicka_prioriterat(
            rubrik,
            tenant_id=tenant_id or "okänd kund",
            vad=vad,
            varfor=varfor,
            nyckel=f"gallring:{tenant_id}:{kund.get('status')}",
        )
    except Exception:  # noqa: BLE001
        logger.warning("Kunde inte skicka gallringslarmet som mejl.")


async def kor_gallring(storage: Any, *, nu: datetime | None = None) -> dict[str, Any]:
    """Ett varv. Returnerar vad som hände: {status, ...}.

    status: 'avstangd', 'for_tidigt', eller gallra_alla:s svar
    ('kord', 'redan_kord', 'ingen_databas'). I en spegel bär svaret
    `spegel: true`, och databasen har då bara gallrat det synken inte för över."""
    settings = get_settings()
    if not settings.gallring_aktiv:
        return {"status": "avstangd"}
    lokal = (nu or datetime.now(_SVERIGE)).astimezone(_SVERIGE)
    if lokal.hour < settings.gallring_timme:
        return {"status": "for_tidigt"}

    tak = max(int(settings.gallring_tak), 0)
    svar = await storage.gallra_dygnet(tak=tak)
    if svar.get("status") != "kord":
        return svar

    kunder = svar.get("kunder") or []
    for kund in kunder:
        if kund.get("status") in ("tak_nadd", "fel"):
            await _larma(storage, kund, tak=tak)
    logger.info(
        "Gallringen %s: %s kunder, %s rader, %s vid taket, %s fel.",
        svar.get("dag"),
        len(kunder),
        sum(int(k.get("totalt") or 0) for k in kunder if k.get("status") == "klar"),
        sum(1 for k in kunder if k.get("status") == "tak_nadd"),
        sum(1 for k in kunder if k.get("status") == "fel"),
    )
    return svar


async def run_gallring(app_state: Any) -> None:
    """Bakgrundsloopen. Tittar en gång i timmen; dygnsspärren i databasen gör
    att körningen sker högst en gång per dygn, hur många processer som än tittar."""
    intervall = max(get_settings().gallring_kontroll_sekunder, 300)
    logger.info("Gallringen aktiv: kontroll var %s sekund.", intervall)
    while True:
        try:
            await kor_gallring(app_state.storage)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — gallringen får aldrig fälla tjänsten
            logger.exception("Oväntat fel i gallringen — försöker igen nästa varv.")
        await asyncio.sleep(intervall)
