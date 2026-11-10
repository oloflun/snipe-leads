"""Leads-budgetgrinden: ett kostnadstak där inget fanns alls.

Leads-endpointsen har (till skillnad från chat/triage/demo, som går genom
rate_limit_db) aldrig haft något tak — en enda batch är upp till 50 prospekt
och varje prospekt är flera LLM-anrop. Uppmätt 2026-09-01: en omkörning av
18 leads kostade ~18 kr, och en återtagsbugg (se INV-JOB-002) dubblerade den
utan användarhandling. Grinden här är sista försvarslinjen mot båda: hur
felet än uppstår kan en tenant inte bränna mer än budgeten per dygn.

Taket räknas på agent_runs-tokens (LEADS_BUDGET_AGENT_TYPES i
storage/base.py) över ett rullande 24-timmarsfönster, INKLUSIVE
testkörningar — de kostar samma pengar hos leverantören. Nivån styrs av
settings.leads_daily_token_budget (env LEADS_DAILY_TOKEN_BUDGET); 0 stänger
av grinden.

Förvarning (2026-11-09): vid 80 % av taket skrivs en varning till
platform_events, en gång per kund och dygn, och när taket slår skrivs ett fel.
Förut märktes taket först när en kund fick nej. Kundens besked nämner varken
tokens eller miljövariabler; siffrorna står i händelsen och i loggen.

Anropas från körningsstarterna i app/api/leads.py (batch, processa-om,
direktutkast) — INNAN något köas. Ett jobb som redan står i kön stoppas
inte retroaktivt: grinden är en dörr, inte en vakt inne i rummet.
"""

from __future__ import annotations

import logging
from datetime import date

from ..config import get_settings

logger = logging.getLogger("snajp-support.leads-budget")

#: Andel av taket där förvarningen går (samma som supportens, app/budget.py).
FORVARNING_ANDEL = 0.8

#: Det kunden läser när taket är nått.
KUNDTEXT_BUDGET = (
    "Dygnstaket för leadskörningar är nått. Nya körningar går att starta igen "
    "inom ett dygn. Kontakta Snajp om ni behöver köra mer i dag."
)


class LeadsBudgetExceededError(Exception):
    """Budgeten är förbrukad — API-lagret översätter till HTTP 429."""


async def _larma(storage, tenant_id: str, *, niva: str, forbrukat: int, tak: int) -> None:
    """Förvarning ('80') eller taket nått ('100'). En gång per kund, nivå och
    dygn i den här processen. Kastar aldrig: larmet får inte fälla körningen."""
    from ..budget import _redan_larmat

    if _redan_larmat(f"leadsbudget:{niva}:{tenant_id}:{date.today().isoformat()}"):
        return
    andel = round(100 * forbrukat / tak) if tak else 0
    text = (
        f"Leadsbudgeten är på {andel} % ({forbrukat:,} av {tak:,} tokens senaste dygnet)"
        + ("" if niva == "80" else ": nya körningar avvisas")
    )
    logger.warning("%s (kund %s)", text, tenant_id)
    try:
        await storage.log_platform_event(
            level="warning" if niva == "80" else "error",
            source="budget",
            message=text,
            tenant_id=tenant_id,
            detail={"forbrukat": forbrukat, "tak": tak, "niva": niva, "agent": "leads"},
        )
    except Exception:  # noqa: BLE001
        logger.warning("leadsbudget: kunde inte skriva larmet till platform_events")


async def kontrollera_leads_budget(storage, tenant_id: str) -> None:
    """Kastar LeadsBudgetExceededError om tenantens leads-tokenförbrukning
    senaste 24 h är över taket. Tyst retur annars (eller när taket är 0)."""
    tak = get_settings().leads_daily_token_budget
    if tak <= 0:
        return
    forbrukat = await storage.sum_leads_tokens(tenant_id, hours=24)
    if forbrukat < tak:
        if forbrukat >= FORVARNING_ANDEL * tak:
            await _larma(storage, tenant_id, niva="80", forbrukat=forbrukat, tak=tak)
        return
    await _larma(storage, tenant_id, niva="100", forbrukat=forbrukat, tak=tak)
    raise LeadsBudgetExceededError(KUNDTEXT_BUDGET)
