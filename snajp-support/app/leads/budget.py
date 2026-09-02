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

Anropas från körningsstarterna i app/api/leads.py (batch, processa-om,
direktutkast) — INNAN något köas. Ett jobb som redan står i kön stoppas
inte retroaktivt: grinden är en dörr, inte en vakt inne i rummet.
"""

from __future__ import annotations

from ..config import get_settings


class LeadsBudgetExceededError(Exception):
    """Budgeten är förbrukad — API-lagret översätter till HTTP 429."""


async def kontrollera_leads_budget(storage, tenant_id: str) -> None:
    """Kastar LeadsBudgetExceededError om tenantens leads-tokenförbrukning
    senaste 24 h är över taket. Tyst retur annars (eller när taket är 0)."""
    tak = get_settings().leads_daily_token_budget
    if tak <= 0:
        return
    forbrukat = await storage.sum_leads_tokens(tenant_id, hours=24)
    if forbrukat < tak:
        return
    raise LeadsBudgetExceededError(
        "Dygnsbudgeten för leads-körningar är förbrukad "
        f"({forbrukat:,} av {tak:,} tokens de senaste 24 timmarna). "
        "Nya körningar går att starta när fönstret rullat vidare — "
        "eller höj LEADS_DAILY_TOKEN_BUDGET om taket är fel satt."
    )
