"""Vem som når Snajp CRM: tillägget, eller en provperiod som inte gått ut.

Antons svar 2026-11-26: CRM:et är ett tillägg, med fri tillgång under
provperioden. Tillägget är nyckeln `crm` på arbetsytan (workspaces.addons,
migration 161) och provperioden är workspaces.trial_slut (migration 074).

Grinden sitter i backenden och inte bara i webben, till skillnad från
tillägget leadslistor: CRM:et har ett publikt API som nås med en nyckel utan
att passera webben, och en grind som bara fanns i webben hade inte gällt där.

En kund utan kopplad arbetsyta (configfil-kunder, demokunden) släpps igenom,
som i `require_bookkeeping_tenant`: där finns inget tillägg att läsa, och att
stänga på okänt hade fällt varje kund som lades upp före arbetsytorna.

Svaret sparas en minut per kund, så att ett API som tar 600 anrop i minuten
inte gör 600 uppslag.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

TILLAGG = "crm"
_SEKUNDER = 60.0
_sparat: dict[str, tuple[float, bool]] = {}


def nollstall() -> None:
    """Glömmer sparade svar. Anropas när ett tillägg ändras, och i tester."""
    _sparat.clear()


def _datum(varde: Any) -> date | None:
    if isinstance(varde, datetime):
        return varde.date()
    if isinstance(varde, date):
        return varde
    try:
        return date.fromisoformat(str(varde)[:10]) if varde else None
    except ValueError:
        return None


def avgor(grund: dict[str, Any] | None, idag: date) -> bool:
    """Regeln, utan databas: `grund` är arbetsytans tillägg och provperiodens
    sista dag, eller None när kunden saknar arbetsyta."""
    if grund is None:
        return True
    if TILLAGG in (grund.get("addons") or []):
        return True
    slut = _datum(grund.get("trial_slut"))
    return slut is not None and slut >= idag


async def grund(storage: Any, tenant_id: str) -> dict[str, Any] | None:
    """Arbetsytans tillägg och provperiod. Oskopad läsning, samma väg och
    samma policy som `get_tenant_products` (064): `workspaces` bär
    workspace-RLS, och en tenant-skopad anslutning ser noll rader. Den
    tidigast skapade arbetsytan vinner när flera delar kund."""
    if hasattr(storage, "pool") and hasattr(storage, "_scoped"):
        async with storage.pool.acquire() as conn:
            rad = await conn.fetchrow(
                "select addons, trial_slut from workspaces where ss_tenant_id = $1 "
                "order by created_at limit 1", tenant_id)
        return None if rad is None else {"addons": list(rad["addons"] or []), "trial_slut": rad["trial_slut"]}
    return getattr(storage, "_crm_tillgang", {}).get(str(tenant_id))


async def har_tillgang(storage: Any, tenant_id: str) -> bool:
    nyckel = str(tenant_id)
    nu = time.monotonic()
    traff = _sparat.get(nyckel)
    if traff and nu - traff[0] < _SEKUNDER:
        return traff[1]
    svar = avgor(await grund(storage, nyckel), datetime.now(timezone.utc).date())
    _sparat[nyckel] = (nu, svar)
    return svar
