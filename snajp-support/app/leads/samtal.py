"""Ringlistan och återkopplingen (leadsregel 15 och 17, Antons beställning 2026-10-07).

Två listor över samma sorts arbete, att ringa ett bolag:

* **Återkoppling:** Iris-leads som fått mejl (status `contacted`) och har ett
  telefonnummer, äldst kontakt först.
* **Ringlista:** bolag med bara telefon och namngiven VD (`origin='ring'`).

Varje samtal sparas i `lead_samtal` (migration 107) med ett utfall. Utfallet
flyttar prospektets status i samma anrop, så att mejlflödet och listorna
aldrig är oense: ej intresserad → `lost`, kontakta inte → `suppressed` (och
adressen spärras), möte → `meeting`. De tre avslutar leadet och stoppar allt
som väntar på att skickas. Ej svar och återkom håller leadet kvar; systemet
tar fram det igen när det är dags (`nasta_samtal`). Ett mejlsvar flyttar
statusen i app/leads/svar.py, och då försvinner leadet ur återkopplingen av
sig självt eftersom listan bara tar `contacted`.

Uppföljningsmejlen kommer från uppföljningssvepet på sitt eget schema, alltid
som utkast till granskning; samtalen och mejlen går parallellt.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from .scheduler import avbryt_utskick_for_prospekt
from .timing_gate import swedish_no_send_dates

Utfall = Literal["ej_svar", "aterkom", "ej_intresserad", "kontakta_inte", "mote"]

#: Utfall som avslutar leadet: statusen det får.
AVSLUTANDE: dict[str, str] = {"ej_intresserad": "lost", "kontakta_inte": "suppressed", "mote": "meeting"}

#: Ett obesvarat samtal kommer tillbaka efter så många arbetsdagar.
EJ_SVAR_ARBETSDAGAR = 2

_KLARA = {"lost", "suppressed", "meeting", "won"}
_EJ_PROSPEKT = {"example", "test"}


def _datum(varde: Any) -> date | None:
    if varde in (None, ""):
        return None
    if isinstance(varde, datetime):
        return varde.astimezone(timezone.utc).date() if varde.tzinfo else varde.date()
    if isinstance(varde, date):
        return varde
    text = str(varde)
    return datetime.fromisoformat(text).date() if "T" in text or " " in text else date.fromisoformat(text)


def plus_arbetsdagar(fran: date, antal: int) -> date:
    """Hoppar över helger och de svenska helgdagar då vi inte heller mejlar."""
    dag = fran
    while antal > 0:
        dag += timedelta(days=1)
        if dag.weekday() < 5 and dag not in swedish_no_send_dates(dag.year):
            antal -= 1
    return dag


def nasta_samtal(senaste: dict[str, Any] | None) -> date | None:
    """Dagen leadet ska ringas nästa gång. None = aldrig (avslutat).
    Inget samtal än = i dag (date.min sorterar först)."""
    if senaste is None:
        return date.min
    utfall = senaste.get("utfall")
    if utfall in AVSLUTANDE:
        return None
    if utfall == "aterkom":
        return _datum(senaste.get("aterkom_datum")) or date.min
    return plus_arbetsdagar(_datum(senaste.get("created_at")) or date.min, EJ_SVAR_ARBETSDAGAR)


def samtalslista(
    prospekter: list[dict[str, Any]],
    samtal: list[dict[str, Any]],
    forsta_kontakt: dict[str, Any],
    *,
    lista: Literal["aterkoppling", "ring"],
    idag: date,
) -> list[dict[str, Any]]:
    """Raderna i en lista, de som ska ringas i dag först, sedan äldst först.

    `samtal` är tenantens samtal i skapandeordning; `forsta_kontakt` är
    prospekt-id → första skickade mejlets tid."""
    per_prospekt: dict[str, list[dict[str, Any]]] = {}
    for rad in samtal:
        per_prospekt.setdefault(str(rad["prospect_id"]), []).append(rad)

    rader = []
    for p in prospekter:
        if p.get("arkiverad_at") or p.get("origin") in _EJ_PROSPEKT:
            continue
        if lista == "ring":
            if p.get("origin") != "ring" or p.get("status") in _KLARA:
                continue
        elif p.get("origin") == "ring" or p.get("status") != "contacted" or not p.get("contact_phone"):
            continue
        pid = str(p["id"])
        historik = per_prospekt.get(pid, [])
        senaste = historik[-1] if historik else None
        nasta = nasta_samtal(senaste)
        if nasta is None:
            continue
        kontaktad = _datum(forsta_kontakt.get(pid))
        rader.append(
            {
                "prospect_id": pid,
                "company_name": p.get("company_name"),
                "ort": p.get("ort"),
                "website": p.get("website"),
                "contact_name": p.get("contact_name"),
                "contact_role": p.get("contact_role"),
                "contact_phone": p.get("contact_phone"),
                "contact_email": p.get("contact_email"),
                "anstallda": p.get("anstallda"),
                "status": p.get("status"),
                "kontaktad": kontaktad.isoformat() if kontaktad else None,
                "antal_samtal": len(historik),
                "senaste_utfall": senaste.get("utfall") if senaste else None,
                "senaste_samtal": str(senaste["created_at"]) if senaste else None,
                "aterkom_datum": str(senaste["aterkom_datum"]) if senaste and senaste.get("aterkom_datum") else None,
                "nasta": None if nasta == date.min else nasta.isoformat(),
                "ring_idag": nasta <= idag,
                "_ordning": kontaktad or _datum(p.get("created_at")) or date.min,
                "_nasta": nasta,
            }
        )
    rader.sort(key=lambda r: (not r["ring_idag"], r["_nasta"] if not r["ring_idag"] else date.min, r["_ordning"]))
    for r in rader:
        del r["_ordning"], r["_nasta"]
    return rader


async def registrera(
    storage: Any,
    tenant_id: str,
    prospect: dict[str, Any],
    *,
    utfall: Utfall,
    aterkom_datum: date | None,
    anteckning: str | None,
) -> dict[str, Any]:
    """Sparar samtalet och verkställer utfallet. Returnerar samtalsraden."""
    pid = str(prospect["id"])
    rad = await storage.add_lead_samtal(
        tenant_id, prospect_id=pid, utfall=utfall,
        aterkom_datum=aterkom_datum.isoformat() if aterkom_datum else None,
        anteckning=anteckning,
    )
    ny_status = AVSLUTANDE.get(utfall)
    if ny_status:
        await avbryt_utskick_for_prospekt(storage, tenant_id, pid)
        if utfall == "kontakta_inte" and prospect.get("contact_email"):
            await storage.add_suppression(tenant_id, email=prospect["contact_email"], reason="kontakta inte (samtal)")
    elif prospect.get("status") in ("new", "ready"):
        # Ett samtal till ett bolag på ringlistan är en kontakt.
        ny_status = "contacted"
    if ny_status and ny_status != prospect.get("status"):
        await storage.update_prospect(tenant_id, pid, status=ny_status, status_kalla="manuell")
    return rad
