"""Leads Fas E (Del F): positivt svar -> eskalera till mötesbokning ->
sa:call-prep förbereder människan som tar över -> överlämning.

Agenten bokar ALDRIG själv och förhandlar ALDRIG pris — det är inte en
regel agenten "vet om", det är en strukturell begränsning: leads-agentens
verktygslista innehåller inget boknings- eller prisförhandlingsverktyg
(samma mönster som G3: "kan bara köa" för sändvägen). Den kan bara flagga
för handoff.

Överlämningens ROUTING (vem hos kunden, hur snabbt) är EGEN LOGIK här, inte
en skill — mk:revops utgick ur planen (Del I) eftersom den förutsätter ett
CRM med pipeline-stadier och ett säljteam att dirigera leads mellan; det vi
behöver är två stycken ur den (Routing Methods, Speed-to-Lead), inte en
hel skill-injektion.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..agentcore.packs import Playbook, PlaybookStep, RunLedger, check_preconditions

CALL_PREP_V1 = Playbook(
    name="leads/call-prep-v1",
    steps=(PlaybookStep(skill="sa:call-prep", requires=("positive_reply_confirmed",)),),
)


@dataclass(frozen=True)
class HandoffRecord:
    prospect_id: str
    tenant_id: str
    reason: str
    assigned_to: str | None
    speed_to_lead_target_minutes: int


def route_handoff(
    *, prospect_id: str, tenant_id: str, reason: str, tenant_primary_contact: str | None
) -> HandoffRecord:
    """Egen routinglogik (inte mk:revops). Speed-to-lead: ju snabbare en
    människa hör av sig efter en positiv signal, desto högre svarsfrekvens
    — branschriktmärke 5 minuter för webbleads, vi sätter 30 för att inte
    lova mer än en liten kunds bemanning klarar av."""
    return HandoffRecord(
        prospect_id=prospect_id,
        tenant_id=tenant_id,
        reason=reason,
        assigned_to=tenant_primary_contact,
        speed_to_lead_target_minutes=30,
    )


def render_call_prep_instructions() -> tuple[str, RunLedger]:
    ledger = RunLedger(satisfied={"positive_reply_confirmed"})
    parts: list[str] = [
        "Prospektet har svarat positivt. Förbered den människa som tar över "
        "mötet — du bokar inte själv, du förhandlar inte pris, du bara "
        "sammanställer underlaget.",
    ]
    for step in CALL_PREP_V1.steps:
        check_preconditions(step, ledger)
        rendered = step.render()
        ledger.mark_skill_injected(step.skill)
        ledger.executed_order.append(step.skill)
        parts.append(f"---\n### Skill: {step.skill}\n{rendered}")
    return "\n\n".join(parts), ledger
