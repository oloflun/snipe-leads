"""Städaren: leads-jobb och leadslistor som ingen längre kör får ett ärligt slut.

## Problemet

Ett leads-jobb skrivs i tre lager — Redis-jobbposten (app/jobs/store.py),
liggaren `leads_job_ledger` (migration 059) och, för listor, `lead_lists`
(migration 060). Bara Redis-posten hade någon form av tidsgräns, och den
slog till LATT: först när någon läste posten, och posten TTL:ar bort efter en
timme. Liggaren och listraden hade ingenting. Dog processen mitt i en körning
(deploy, OOM, en 429-sömn som aldrig vaknade), eller gav strömmen upp en post
efter MAX_LEVERANSER, stod raderna kvar i `processing`/`byggs` för evigt.

Uppmätt av testaren 2026-09-13: en leadslista låg i "byggs" i dagar med tre
halvfärdiga rader, och ingenting i systemet skulle någonsin ändra det. Kunden
såg en snurra och tre skräprader.

## Lösningen

`stada_tenant` markerar liggarrader i queued/processing och listor i
bestalld/byggs som är ÄLDRE än `leads_hangtid_minuter` som misslyckade, med en
svensk mening som säger vad som hänt. En städad listas rader tas bort — en
lista som inte blev klar ska inte visa en halv tabell som om den vore svaret.

Den körs på tre ställen:

  1. vid API-uppstart (första varvet i `run_leads_stadare`),
  2. periodiskt var `leads_stadning_sekunder` (samma bakgrundsmönster som
     send_queue-schemaläggaren i app/leads/scheduler.py),
  3. lat, när kunden läser sina listor (GET /api/leads/listor[/{id}]).

## Varför klockan räknar från created_at, och varför det är ofarligt

Liggaren har ingen uppdaterad-kolumn, och en migration bara för en livssignal
vore en deployordningsfälla (koden skriver kolumnen innan den finns — se
kommentaren sist i migration 059). Tröskeln är därför generös (default 60
min, räknat från köandet) och två skydd gör en felaktig städning självläkande
i stället för skadlig:

  * Jobb som körs i DEN HÄR processen står i `_aktiva` och städas aldrig.
  * En städad men i själva verket köad post körs ändå när workern når den:
    liggarvakten hoppar bara över `completed`, och körningen skriver sedan
    sin egen slutstatus. Listjobbet skriver dessutom sina rader FÖRST när
    hela bygget lyckats (se _run_list_job), så det finns inga rader att
    städa bort under ett pågående bygge.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..config import get_settings

logger = logging.getLogger("snajp-support.jobs.stadare")

#: Kundens besked för ett jobb som städats. Ingen gissning om orsaken utöver
#: det vi vet: körningen tog aldrig slut. "Kör om" är sant — ett nytt jobb
#: startar från början.
HANGFEL_JOBB = (
    "Körningen avbröts innan den blev klar — troligen av en omstart hos oss — "
    "och har markerats som misslyckad. Kör om den."
)

#: Listans felorsak efter städning. "Inga halvfärdiga rader sparades" är ett
#: löfte städningen håller (raderna tas bort i samma svep).
HANGFEL_LISTA = (
    "Listbygget avbröts innan det blev klart — troligen av en omstart hos oss. "
    "Inga halvfärdiga rader sparades. Beställ listan igen."
)

#: Besked när strömmen gett upp en post efter MAX_LEVERANSER (app/jobs/stream.py).
UPPGIVET_JOBB = (
    "Körningen kunde inte slutföras efter upprepade försök och har markerats "
    "som misslyckad. Felet är loggat hos oss — kör om den."
)
UPPGIVET_LISTA = (
    "Listan kunde inte byggas efter upprepade försök. Felet är loggat hos oss "
    "och inga halvfärdiga rader sparades — beställ listan igen."
)

#: job_id/list_id som körs i DEN HÄR processen just nu -> antal pågående.
#: Räknare och inte mängd: samma id kan i sällsynta fall köras två gånger
#: samtidigt (ett återtag som överlappar), och den första som blir klar får
#: inte avregistrera den andra.
_aktiva: dict[str, int] = {}


def registrera_aktiv(*nycklar: str | None) -> None:
    for nyckel in nycklar:
        if nyckel:
            _aktiva[nyckel] = _aktiva.get(nyckel, 0) + 1


def avregistrera_aktiv(*nycklar: str | None) -> None:
    for nyckel in nycklar:
        if not nyckel or nyckel not in _aktiva:
            continue
        _aktiva[nyckel] -= 1
        if _aktiva[nyckel] <= 0:
            del _aktiva[nyckel]


def aktiva() -> list[str]:
    return sorted(_aktiva)


async def faila_jobb_om_oppet(jobs: Any, job_id: str, text: str) -> None:
    """Markerar Redis-/minnesposten failed — men bara om den finns och inte
    redan är avslutad. RedisJobStore.fail skapar annars en ny post ur
    ingenting (dess _merge börjar från {}), och en städning ska aldrig
    skriva över ett jobb som faktiskt blev klart."""
    if jobs is None:
        return
    try:
        post = await jobs.get(job_id)
    except Exception:  # noqa: BLE001 — en Redis-hicka får inte stoppa städningen
        logger.exception("Kunde inte läsa jobbposten %s under städningen.", job_id)
        return
    if post and post.get("status") not in ("completed", "failed"):
        await jobs.fail(job_id, text)


async def stada_tenant(
    app_state: Any, tenant_id: str, *, minuter: int | None = None
) -> dict[str, list[str]]:
    """Städar EN tenants hängande leads-jobb och listor. Returnerar vad som
    städades: {"jobb": [job_id, ...], "listor": [list_id, ...]}."""
    grans = get_settings().leads_hangtid_minuter if minuter is None else minuter
    if grans <= 0:
        return {"jobb": [], "listor": []}
    storage = app_state.storage
    utom = aktiva()
    jobb = await storage.stada_hangande_leadsjobb(tenant_id, aldre_an_minuter=grans, utom=utom)
    listor = await storage.stada_hangande_leadslistor(
        tenant_id, aldre_an_minuter=grans, felorsak=HANGFEL_LISTA, utom=utom
    )
    jobs = getattr(app_state, "jobs", None)
    for job_id in jobb:
        await faila_jobb_om_oppet(jobs, job_id, HANGFEL_JOBB)
    if jobb or listor:
        logger.warning(
            "Städade hängande leads-arbete för %s: %d jobb, %d listor (äldre än %d min).",
            tenant_id,
            len(jobb),
            len(listor),
            grans,
        )
        try:
            await storage.log_platform_event(
                level="warning",
                source="leads",
                message=(
                    f"Städaren avslutade {len(jobb)} hängande leads-jobb och "
                    f"{len(listor)} hängande listor"
                ),
                tenant_id=tenant_id,
                detail={"jobb": jobb, "listor": listor, "aldre_an_minuter": grans},
            )
        except Exception:  # noqa: BLE001 — händelseloggen får inte fälla städningen
            logger.warning("kunde inte skriva städningen till platform_events")
    return {"jobb": jobb, "listor": listor}


async def stada_alla(app_state: Any) -> dict[str, dict[str, list[str]]]:
    """Ett svep över alla aktiva tenants. En trasig tenant stoppar inte de andra."""
    resultat: dict[str, dict[str, list[str]]] = {}
    for tenant in await app_state.storage.list_tenants():
        try:
            utfall = await stada_tenant(app_state, tenant["id"])
        except Exception:  # noqa: BLE001 — se docstringen
            logger.exception("Städningen misslyckades för tenant %s.", tenant.get("id"))
            continue
        if utfall["jobb"] or utfall["listor"]:
            resultat[tenant["id"]] = utfall
    return resultat


async def run_leads_stadare(app_state: Any) -> None:
    """Bakgrundsloopen. Första svepet direkt — det ÄR uppstartsstädningen."""
    intervall = max(get_settings().leads_stadning_sekunder, 30)
    logger.info("Leads-städaren aktiv: var %s sekund.", intervall)
    while True:
        try:
            await stada_alla(app_state)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — städaren får aldrig dö
            logger.exception("Oväntat fel i leads-städaren — fortsätter nästa varv.")
        await asyncio.sleep(intervall)
