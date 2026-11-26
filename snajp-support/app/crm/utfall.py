"""Utfall som gäller åt båda håll: CRM-posten och leadet säger samma sak.

Ett bolag i CRM:et och ett lead hos Iris är samma bolag när de delar nyckel
(`tidslinje.nycklar_for_bolag`). Sätts ett utfall på ena stället ska det gälla
på det andra, annars ringer en säljare ett bolag som bett att slippa.

## Från CRM:et till leadsflödet: `registrera`

Utfallet verkställs av de funktioner leadsflödet redan har, aldrig genom att
CRM:et skriver i leadstabellerna:

- ej svar, återkom, ej intresserad, kontakta inte och möte bokat går genom
  `samtal.registrera`, som sparar samtalet, flyttar leadets status, stoppar
  det som väntar på att skickas och spärrar adressen vid kontakta inte;
- vunnen sätter leadets status och stoppar väntande utskick.

På CRM-posten: kontakta inte märker bolaget (och stoppar därmed utskick till
dess personer, `lagring.kontakta_inte_adresser`), och vunnen gör bolaget till
kund.

## Från leadsflödet till CRM:et: `iris_lage`

Leadets läge läses när posten visas, det kopieras inte. Har ett av bolagets
leads bett att slippa kontakt (status `suppressed`) gäller det bolaget i
CRM:et också, vad posten själv än säger: Snajps avslutande utfall vinner
alltid över ett värde i CRM:et som skulle öppna leadet igen.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from ..leads import samtal
from ..leads.scheduler import avbryt_utskick_for_prospekt
from . import synk, tidslinje

#: Utfallen CRM:et kan sätta. De fem första är samtalets egna (leadsregel 17).
UTFALL = ("ej_svar", "aterkom", "ej_intresserad", "kontakta_inte", "mote", "vunnen")

#: Leadets status när det inte ska bearbetas mer, och vad det betyder i CRM:et.
_AVSLUTAT = {"suppressed": "kontakta_inte", "lost": "ej_intresserad", "meeting": "mote", "won": "vunnen"}


class OgiltigtUtfall(ValueError):
    """Utfallet finns inte, eller återkom saknar datum."""


async def registrera(
    storage: Any, tenant_id: str, bolag: dict[str, Any], *, utfall: str, aterkom_datum: date | None = None,
    anteckning: str | None = None, via: str = "api", aktor: str | None = None,
) -> dict[str, Any]:
    """Verkställer utfallet i leadsflödet och på CRM-posten.

    Returnerar `{"bolag": posten efteråt, "leads": id på de leads som berördes}`.
    Ett bolag utan lead får bara CRM-sidans följd.
    """
    if utfall not in UTFALL:
        raise OgiltigtUtfall("okant_utfall")
    if utfall == "aterkom" and aterkom_datum is None:
        raise OgiltigtUtfall("aterkom_kraver_datum")
    berorda: list[str] = []
    for rad in await tidslinje.prospekt_for_bolag(storage, tenant_id, bolag):
        prospekt = await storage.get_prospect(tenant_id, str(rad["id"]))
        if prospekt is None:
            continue
        pid = str(prospekt["id"])
        if utfall == "vunnen":
            await avbryt_utskick_for_prospekt(storage, tenant_id, pid)
            if prospekt.get("status") != "won":
                await storage.update_prospect(tenant_id, pid, status="won", status_kalla="manuell")
        else:
            await samtal.registrera(storage, tenant_id, prospekt, utfall=utfall,
                                    aterkom_datum=aterkom_datum if utfall == "aterkom" else None,
                                    anteckning=(anteckning or "").strip() or None)
        berorda.append(pid)

    andring: dict[str, Any] = {}
    if utfall == "kontakta_inte" and not bolag.get("kontakta_inte"):
        andring["kontakta_inte"] = True
    if utfall == "vunnen":
        if bolag.get("relation") != "kund":
            andring["relation"] = "kund"
        if not bolag.get("kund_sedan"):
            andring["kund_sedan"] = datetime.now(timezone.utc).date().isoformat()
    ny = bolag
    if andring:
        ny = await synk.andra(storage, tenant_id, "bolag", bolag["id"], andring, via=via, aktor=aktor) or bolag
    return {"bolag": ny, "leads": berorda}


async def iris_lage(storage: Any, tenant_id: str, bolag: dict[str, Any]) -> dict[str, Any]:
    """Bolagets leads hos Iris och vad de betyder för posten.

    `kontakta_inte` är sant om posten själv säger det ELLER om ett av bolagets
    leads bett att slippa kontakt. `utfall` är leadsflödets avslutande utfall,
    det starkaste först: kontakta inte, vunnen, möte, ej intresserad.
    """
    leads = [{"id": str(p["id"]), "namn": p.get("company_name"), "status": p.get("status"),
              "created_at": str(p["created_at"]) if p.get("created_at") else None}
             for p in await tidslinje.prospekt_for_bolag(storage, tenant_id, bolag)]
    statusar = {lead["status"] for lead in leads}
    utfall = next((_AVSLUTAT[s] for s in ("suppressed", "won", "meeting", "lost") if s in statusar), None)
    return {"leads": leads, "utfall": utfall,
            "kontakta_inte": bool(bolag.get("kontakta_inte")) or "suppressed" in statusar}
