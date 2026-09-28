"""Supportbudgeten: ett dygnstak i tokens per tenant, med förvarning.

## Varför en egen grind bredvid rate_limit_db

Timtaket (400 LLM-anrop/h, migration 019) skyddar mot skov men inte mot en
jämn ström: 24 timmar strax under timtaket är en räkning ingen beställt.
Leads fick sitt dygnstak efter 18-kronorsincidenten (app/leads/budget.py,
INV-JOB-002); det här är supportens motsvarighet, byggd för
Livrustning-piloten där en publik chattwidget och en riktig kundbas möter
den delade API-budgeten för första gången.

## Nivåer

Taket läses i den här ordningen — första träffen vinner:

  1. env `SUPPORT_BUDGET_<SLUG>` (t.ex. SUPPORT_BUDGET_LIVRUSTNING) — samma
     namnmönster som IMAP_PASSWORD_<SLUG> i email_pipeline/poller.py.
  2. `SUPPORT_DAILY_TOKEN_BUDGET` (settings.support_daily_token_budget) —
     gäller alla tenants i miljön.
  3. 0 = grinden avstängd. Default, så befintliga kunder inte får ett tak
     de aldrig haft av en kodändring — taket sätts per miljö, som leads.

## Förvarning — det som INTE fanns förut

Vid 80 % av taket skrivs en warning till platform_events och ETT prioriterat
mejl går till oss (deduplicerat per tenant och dygn). Innan detta larmade
systemet först när något redan var trasigt; ett tak man upptäcker när det
slagit till är ett tak som redan kostat en kunds förtroende.

Räknat på `agent_runs` med agent_type 'support' över rullande 24 h,
testkörningar MEDräknade — de kostar samma pengar hos leverantören.
E-postpipelinens fristående triage-anrop loggas inte som agent_runs och
syns därför inte i summan; grinden prövas ändå där, så ett stängt tak
stoppar även mejlprocessningen.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date

from .config import get_settings

logger = logging.getLogger("snajp-support.budget")

#: Andel av taket där förvarningen går.
FORVARNING_ANDEL = 0.8

#: Vad kunden ska läsa när taket är nått. Ärligt om att det är ett tak, utan
#: att be kunden "försöka igen om en stund" — fönstret är ett dygn.
KUNDTEXT_BUDGET = (
    "Chatten har nått sitt kapacitetstak för dygnet. Kontakta oss gärna via "
    "mejl så återkommer vi — eller försök igen i morgon."
)

#: tenant:datum -> när vi larmade. Processlokal av samma skäl (och med samma
#: felriktning) som dubblettminnet i notifications/prioriterat_mejl.py.
_larmade: dict[str, float] = {}
_LARMFONSTER_SEKUNDER = 24 * 60 * 60


class SupportBudgetExceededError(Exception):
    """Dygnsbudgeten är förbrukad — API-lagret översätter till HTTP 429."""


def nollstall_larmminne() -> None:
    """Bara för tester."""
    _larmade.clear()


def _miljonamn(slug: str) -> str:
    return "SUPPORT_BUDGET_" + slug.upper().replace("-", "_")


def budget_for(slug: str | None) -> int:
    """Taket för en tenant, i tokens per rullande dygn. 0 = av."""
    if slug:
        varde = (os.environ.get(_miljonamn(slug)) or "").strip()
        if varde:
            try:
                return max(0, int(varde))
            except ValueError:
                logger.warning(
                    "budget: %s=%r är inte ett tal — faller tillbaka på det globala taket",
                    _miljonamn(slug),
                    varde,
                )
    return max(0, get_settings().support_daily_token_budget)


def _redan_larmat(nyckel: str) -> bool:
    nu = time.monotonic()
    for gammal, sedd in list(_larmade.items()):
        if nu - sedd > _LARMFONSTER_SEKUNDER:
            del _larmade[gammal]
    if nyckel in _larmade:
        return True
    _larmade[nyckel] = nu
    return False


async def _larma(
    storage, *, tenant_id: str, slug: str, niva: str, forbrukat: int, tak: int
) -> None:
    """Förvarning (warning) eller taknått (error). Kastar aldrig."""
    nyckel = f"supportbudget:{niva}:{slug}:{date.today().isoformat()}"
    if _redan_larmat(nyckel):
        return
    andel = round(100 * forbrukat / tak) if tak else 0
    try:
        await storage.log_platform_event(
            level="warning" if niva == "80" else "error",
            source="budget",
            message=(
                f"Supportbudgeten för {slug} är på {andel} % "
                f"({forbrukat:,} av {tak:,} tokens senaste dygnet)"
                + ("" if niva == "80" else " — nya körningar avvisas")
            ),
            tenant_id=tenant_id,
            detail={"forbrukat": forbrukat, "tak": tak, "niva": niva},
        )
    except Exception:  # noqa: BLE001 — larmet får aldrig fälla körningen
        logger.warning("budget: kunde inte skriva larmet till platform_events")

    try:
        from .notifications.prioriterat_mejl import skicka_prioriterat

        await skicka_prioriterat(
            (
                f"Supportbudgeten för {slug} närmar sig taket ({andel} %)"
                if niva == "80"
                else f"Supportbudgeten för {slug} är slut — chatten avvisar"
            ),
            tenant_id=tenant_id,
            vad=(
                f"{forbrukat:,} av {tak:,} tokens förbrukade senaste dygnet "
                f"(agent_runs, agent_type=support)."
            ),
            varfor=(
                "Förvarning vid 80 % — inget är stoppat ännu, men takten avgör "
                "om taket behöver höjas eller trafiken undersökas."
                if niva == "80"
                else "Taket är nått: chatt, mejlprocessning och kanaler svarar "
                f"med kapacitetsbeskedet tills fönstret rullat vidare. Höj "
                f"{_miljonamn(slug)} om taket är fel satt."
            ),
            lank="/admin/handelser",
            nyckel=nyckel,
        )
    except Exception:  # noqa: BLE001
        logger.warning("budget: kunde inte skicka budgetlarmet")


async def kontrollera_support_budget(storage, tenant_id: str) -> None:
    """Kastar SupportBudgetExceededError när dygnstaket är nått; larmar vid
    80 %. Tyst retur när grinden är avstängd. Fail-open vid lagringsfel —
    samma motivering som rate_limit_db: en trasig mätning får inte bli ett
    kundavbrott."""
    try:
        tenant = await storage.get_tenant(tenant_id)
        slug = (tenant or {}).get("slug") or ""
        tak = budget_for(slug)
        if tak <= 0:
            return
        forbrukat = await storage.sum_support_tokens(tenant_id, hours=24)
    except Exception as fel:  # noqa: BLE001 — fail-open är avsiktligt
        logger.warning(
            "budget: uppslaget för tenant %s misslyckades, släpper igenom (%s)",
            tenant_id,
            fel,
        )
        return

    if forbrukat >= tak:
        await _larma(
            storage, tenant_id=tenant_id, slug=slug, niva="100",
            forbrukat=forbrukat, tak=tak,
        )
        raise SupportBudgetExceededError(KUNDTEXT_BUDGET)
    if forbrukat >= tak * FORVARNING_ANDEL:
        await _larma(
            storage, tenant_id=tenant_id, slug=slug, niva="80",
            forbrukat=forbrukat, tak=tak,
        )
