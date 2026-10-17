"""Automationsreglerna per lead-typ (plan del F, Fas 10).

Kunden ställer in dem i Iris › Inställningar. De bor i
`agent_configs.settings["automation"]` bredvid eskaleringen och verkställs i
KOD på fyra ställen:

  * uppföljningssvepet (`follow_up_generator.trad_som_ar_forfallna`):
    väntetiden före första uppföljningen, 0 = ingen uppföljning alls;
  * inkorgen (`email_pipeline/processor._hantera_lead`): ett nytt inkommande
    lead får research och utkast direkt om `inkorg.utkast_auto`;
  * Flytta till Iris (`api/leads.listan_till_iris`): scope när anroparen
    inte valt ett;
  * Jev-triagen (`leads/jev.triage`): `jev_bortval` False låter Jev bedöma
    men aldrig välja bort.

Standardvärdena är EXAKT beteendet före reglerna fanns, så en kund som aldrig
öppnat inställningarna märker ingenting. Lässidan är tolerant (trasigt blir
standard), skrivsidan strikt (pydantic i `api/schemas.py`) — samma form som
`eskalering.py`.
"""

from __future__ import annotations

import copy
from typing import Any

TYPER = ("iris", "lista", "import", "inkorg")

STANDARD: dict[str, Any] = {
    "per_typ": {
        "iris": {"utkast_auto": True, "uppfoljning_dagar": 4},
        "lista": {"utkast_auto": True, "uppfoljning_dagar": 4},
        "import": {"utkast_auto": True, "uppfoljning_dagar": 4},
        "inkorg": {"utkast_auto": False, "uppfoljning_dagar": 4},
    },
    "jev_bortval": True,
    # Autopiloten (leads/autopilot.py, Anton 2026-10-10): en Iris-körning per
    # vardag med så många leads. Av som standard.
    "autopilot": {"pa": False, "leads_per_dag": 10},
}

MAX_DAGAR = 60
MAX_LEADS_PER_DAG = 50


def normalisera(ratt: Any) -> dict[str, Any]:
    """Sparat värde → fullständiga regler. Kastar aldrig."""
    regler = copy.deepcopy(STANDARD)
    if not isinstance(ratt, dict):
        return regler
    if isinstance(ratt.get("jev_bortval"), bool):
        regler["jev_bortval"] = ratt["jev_bortval"]
    ap = ratt.get("autopilot")
    if isinstance(ap, dict):
        if isinstance(ap.get("pa"), bool):
            regler["autopilot"]["pa"] = ap["pa"]
        antal = ap.get("leads_per_dag")
        if isinstance(antal, (int, float)) and not isinstance(antal, bool):
            regler["autopilot"]["leads_per_dag"] = max(1, min(MAX_LEADS_PER_DAG, int(antal)))
    per_typ = ratt.get("per_typ")
    if not isinstance(per_typ, dict):
        return regler
    for typ in TYPER:
        sparat = per_typ.get(typ)
        if not isinstance(sparat, dict):
            continue
        if isinstance(sparat.get("utkast_auto"), bool):
            regler["per_typ"][typ]["utkast_auto"] = sparat["utkast_auto"]
        dagar = sparat.get("uppfoljning_dagar")
        if isinstance(dagar, (int, float)) and not isinstance(dagar, bool):
            regler["per_typ"][typ]["uppfoljning_dagar"] = max(0, min(MAX_DAGAR, int(dagar)))
    return regler


def typ_av(origin: str | None) -> str:
    """Prospektets härkomst → regeltyp. Allt som inte är en lista, en import
    eller inkorgen är Iris egna (manuellt tillagda räknas dit: Iris researchar
    dem på samma sätt)."""
    return origin if origin in ("inkorg", "import", "lista") else "iris"
