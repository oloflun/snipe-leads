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
kund. Kontakta inte lägger dessutom spärrar i alla kanaler för bolagets
e-post, telefon och organisationsnummer (`sparr.lagg_till`, källan `utfall`).

Anteckningen följer samtalet när det finns ett lead och utfallet går genom
`samtal.registrera`. Vid vunnen, och för ett bolag utan lead, blir den en
aktivitet (typ samtal) på bolaget, så att den inte tappas. Aktivitetens
`utfall` är då API:ts kod (`UTFALL_API`, t.ex. `won`), inte den interna.

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
from . import objekt, sparr, synk, tidslinje

#: Utfallen CRM:et kan sätta. De fem första är samtalets egna (leadsregel 17).
UTFALL = ("ej_svar", "aterkom", "ej_intresserad", "kontakta_inte", "mote", "vunnen")
#: Utfallens svenska namn: rubriken på aktiviteten som bär en anteckning.
UTFALL_NAMN = {"ej_svar": "Ej svar", "aterkom": "Återkom", "ej_intresserad": "Ej intresserad",
               "kontakta_inte": "Kontakta inte", "mote": "Möte bokat", "vunnen": "Vunnen"}
#: Utfallens koder i det publika API:t (`POST /companies/{id}/outcome`). Aktiviteten
#: som bär en anteckning får API:ts kod som `utfall`, så att `outcome` på
#: aktiviteten är samma ord som klienten skickade och som `/iris` svarar med.
UTFALL_API = {"ej_svar": "no_answer", "aterkom": "call_back", "ej_intresserad": "not_interested",
              "kontakta_inte": "do_not_contact", "mote": "meeting_booked", "vunnen": "won"}

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

    # Anteckningen bor på leadets samtal när ett lead finns och utfallet går
    # genom samtalet. Annars (vunnen, eller ett bolag utan lead) sparas den
    # som en aktivitet på bolaget, så att den står på bolagets tidslinje.
    text = (anteckning or "").strip()
    if text and (utfall == "vunnen" or not berorda):
        await objekt.skapa(storage, tenant_id, "aktivitet", {
            "typ": "samtal", "rubrik": UTFALL_NAMN[utfall], "text": text, "utfall": UTFALL_API[utfall],
            "bolag_id": bolag["id"]}, via=via, aktor=aktor)

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
    if utfall == "kontakta_inte":
        await _sparra_bolaget(storage, tenant_id, ny, via=via, aktor=aktor)
    return {"bolag": ny, "leads": berorda}


async def _sparra_bolaget(storage: Any, tenant_id: str, bolag: dict[str, Any], *, via: str, aktor: str | None) -> None:
    """Kontakta inte lägger spärrar i alla kanaler för bolagets e-post, telefon
    och organisationsnummer (migration 166), så att invändningen står kvar med
    orsak och datum också om posten ändras eller raderas. En spärr som redan
    gäller lämnas som den är."""
    for slag, varde in (("epost", bolag.get("epost")), ("telefon", bolag.get("telefon")),
                        ("orgnr", bolag.get("orgnr_nyckel"))):
        if not varde:
            continue
        try:
            await sparr.lagg_till(storage, tenant_id, kanal="alla", slag=slag, varde=varde, orsak="kunden_bad",
                                  kalla="utfall", bolag_id=bolag["id"], via=via, aktor=aktor)
        except sparr.OgiltigSparr:
            # Ett äldre värde som inte går att normalisera: posten spärrar ändå.
            continue


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
    # Det senast skapade leadet, så att en klient inte behöver känna till
    # listans ordning (äldst först). Vid lika tid vinner det sista i listan.
    senaste = None
    for lead in leads:
        if senaste is None or (lead["created_at"] or "") >= (senaste["created_at"] or ""):
            senaste = lead
    return {"leads": leads, "senaste": senaste, "utfall": utfall,
            "kontakta_inte": bool(bolag.get("kontakta_inte")) or "suppressed" in statusar}
