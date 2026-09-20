"""Trial-påminnaren: mejlar kunden 7 dagar och 1 dag innan provperioden går ut.

## Varför den finns

Provperioden är 2 kalendermånader från kontoskapande (workspaces.trial_slut,
migration 074), och beställningen 2026-09-20 var uttrycklig: INGEN tyst
övergång. Kunden ska hinna bestämma sig med produkten framför sig, inte
upptäcka i efterhand att perioden tog slut.

Vad som händer NÄR trialen går ut byggs medvetet inte här — automatisk
konvertering till betalning är ett affärsbeslut som väntar på Anton/Sebbe,
inte en teknisk switch. Den här modulen påminner; den stänger ingenting av.

## Varför skickning sker före loggning

Samma resonemang som email_pipeline/sender.py fast åt andra hållet: en
utebliven påminnelse är ett brutet löfte om "ingen tyst övergång", en
dubblett efter en krasch är bara lite tjatig. Därför skickas mejlet först
och loggas sedan; unikheten per (workspace, typ) i trial_paminnelser gör
varje senare svep omkörningsbart utan dubbletter i normalfallet.

## Varför sveparen vägrar en sändväg som inte levererar

`LoggingSendProvider` "skickar" genom att logga. Hade sveparen loggat
påminnelsen som skickad i det läget hade kunden aldrig fått den och
systemet trott motsatsen — exakt den lögn sender.py:s kontrakt förbjuder.
Utan riktig sändväg görs därför ingenting, med en varning per svep.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from ..config import get_settings
from ..leads.send_provider import get_send_provider

logger = logging.getLogger("snajp-support.trial")

_AMNE = {
    7: "Din provperiod hos Snajp går ut om en vecka",
    1: "Din provperiod hos Snajp går ut imorgon",
}


def _brodtext(namn: str, trial_slut: date, dagar_kvar: int) -> str:
    nar = "om en vecka" if dagar_kvar == 7 else "imorgon"
    return "\n".join(
        [
            "Hej,",
            "",
            f"den fria provperioden för {namn} hos Snajp går ut {nar}, "
            f"den {trial_slut.isoformat()}.",
            "",
            "Vill ni fortsätta använda era agenter efter det hör ni av er till oss,",
            "så går vi igenom paket och pris tillsammans. Ingenting stängs av utan",
            "att vi har pratat med er först.",
            "",
            "Svara på det här mejlet om ni har frågor.",
            "",
            "Vänliga hälsningar",
            "Snajp",
        ]
    )


async def kor_svep(storage: Any, *, idag: date) -> list[dict[str, Any]]:
    """Ett svep: hitta kandidater, skicka, logga. Returnerar det som skickades."""
    provider = get_send_provider()
    kandidater = await storage.list_trial_paminnelse_kandidater(idag=idag)
    if not kandidater:
        return []
    if not provider.levererar:
        logger.warning(
            "Trial-påminnaren har %s kandidat(er) men ingen levererande sändväg — "
            "ingenting skickas och ingenting loggas som skickat.",
            len(kandidater),
        )
        return []

    skickade: list[dict[str, Any]] = []
    for rad in kandidater:
        dagar = int(rad["dagar_kvar"])
        typ = "7_dagar" if dagar == 7 else "1_dag"
        try:
            await provider.send(
                to=rad["email"],
                subject=_AMNE[dagar],
                body=_brodtext(str(rad["name"] or "er arbetsyta"), rad["trial_slut"], dagar),
            )
        except Exception:  # noqa: BLE001 — en trasig adress stoppar inte de andra
            logger.exception(
                "Trial-påminnelsen (%s) till arbetsyta %s kunde inte skickas.",
                typ,
                rad["workspace_id"],
            )
            continue
        await storage.spara_trial_paminnelse(
            workspace_id=rad["workspace_id"], typ=typ, skickad_till=rad["email"]
        )
        skickade.append({"workspace_id": rad["workspace_id"], "typ": typ})
    return skickade


async def run_trial_paminnare(app_state: Any) -> None:
    """Bakgrundsloopen. Första svepet direkt, sedan var N:e sekund.

    Intervallet får vara tätt (default var 6:e timme): svepet är billigt och
    idempotent — kandidatfrågan filtrerar redan loggade påminnelser, så ett
    extra varv kostar en SELECT.
    """
    intervall = max(get_settings().trial_paminnelse_sekunder, 300)
    logger.info("Trial-påminnaren aktiv: var %s sekund.", intervall)
    while True:
        try:
            skickade = await kor_svep(app_state.storage, idag=date.today())
            if skickade:
                logger.info("Trial-påminnaren skickade %s påminnelse(r).", len(skickade))
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — påminnaren får aldrig dö
            logger.exception("Oväntat fel i trial-påminnaren — fortsätter nästa varv.")
        await asyncio.sleep(intervall)
