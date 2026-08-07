"""G8: den publika demoagenten. Ingen kund skapas, inget ärende öppnas,
ingen eskalering (det finns ingen människa på andra sidan i demoläge) —
bara ett grundat svar ur demo-kunskapsbasen, humaniserat. Samma
läsgaranti-mekanism (Del C) som support/v1, en kortare kedja eftersom
cs:ticket-triage/cs:customer-escalation/cs:kb-article alla förutsätter
ett riktigt ärende som demon aldrig skapar.
"""

from __future__ import annotations

from ..agentcore.packs import Playbook, PlaybookStep, RunLedger, check_preconditions

DEMO_V1 = Playbook(
    name="support/demo-v1",
    steps=(
        PlaybookStep(skill="cs:draft-response", requires=("context_pack",)),
        PlaybookStep(skill="snajp:humanizer-svenska", requires=("skill:cs:draft-response",)),
    ),
)

_HEADER = """Du är Snajp-Supports OFFENTLIGA DEMO — ett smakprov, inte en riktig
supportkanal. Ingen kund skapas, inget ärende öppnas, inget eskaleras till
en människa (det finns ingen på andra sidan i det här läget). Svara ENBART
grundat i kunskapsbasen (via search_knowledge_base). Saknas svar: säg det
ärligt — låtsas aldrig att en kollega kopplats in, för det har ingen gjort.

Nämn ALDRIG riktiga kunders namn, data eller ärenden. Demoläget har sin
egen, separata kunskapsbas — delar ingenting med en betalande tenant.
"""


def render_demo_instructions() -> tuple[str, RunLedger]:
    ledger = RunLedger(satisfied={"context_pack"})
    parts: list[str] = [_HEADER]
    for step in DEMO_V1.steps:
        check_preconditions(step, ledger)
        rendered = step.render()
        ledger.mark_skill_injected(step.skill)
        ledger.executed_order.append(step.skill)
        parts.append(f"---\n### Skill: {step.skill}\n{rendered}")
    return "\n\n".join(parts), ledger
