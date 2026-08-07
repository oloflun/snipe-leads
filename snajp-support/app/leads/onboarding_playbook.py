"""Leads Fas A (Del F): onboarding. Bygger kontextpaketet (mk:product-marketing
+ mk:customer-research) och retentionsplaybooken (mk:churn-prevention) — allt
nedströms i Fas B-E läser detta.

Samma arkitekturval som support/v1 (se support_playbook.py): en agentisk
loop, instruktionerna byggda genom förvillkorsgrinden innan agenten
skapas. Skillnaden mot support/v1: `session_start` i stället för
`context_pack` som första förvillkor, eftersom Fas A:s HELA syfte är att
PRODUCERA kontextpaketet — det kan rimligen inte kräva sig självt.
"""

from __future__ import annotations

from ..agentcore.packs import Playbook, PlaybookStep, RunLedger, check_preconditions

ONBOARDING_V1 = Playbook(
    name="leads/onboarding-v1",
    steps=(
        PlaybookStep(skill="mk:product-marketing", requires=("session_start",)),
        PlaybookStep(skill="mk:customer-research", requires=("skill:mk:product-marketing",)),
        PlaybookStep(skill="mk:churn-prevention", requires=("skill:mk:customer-research",)),
    ),
)

_HEADER = """Du hjälper en ny Snajp-kund genom onboarding. Nedan följer, i
bestämd ordning, de skills som styr arbetet.

Ställ frågor SEKTION FÖR SEKTION, aldrig alla på en gång — varje skill är
explicit om det. Om kunden redan besvarat något i ett tidigare varv
(se kontextpaketet nedan om det finns), fråga inte igen.

{existing_context}
"""


def render_onboarding_instructions(*, existing_product_marketing: str | None = None) -> tuple[str, RunLedger]:
    """Bygger instruktionstexten för Fas A genom förvillkorsgrinden. Returnerar
    (instruktionstext, ledger) — ledgern bevisar att alla tre Fas A-skills
    injicerades i ordning."""
    ledger = RunLedger(satisfied={"session_start"})
    existing_block = (
        f"### Redan insamlat kontextdokument\n{existing_product_marketing}"
        if existing_product_marketing
        else "### Inget kontextdokument insamlat ännu — börja från början."
    )
    parts: list[str] = [_HEADER.format(existing_context=existing_block)]

    for step in ONBOARDING_V1.steps:
        check_preconditions(step, ledger)
        rendered = step.render()
        ledger.mark_skill_injected(step.skill)
        ledger.executed_order.append(step.skill)
        parts.append(f"---\n### Skill: {step.skill}\n{rendered}")

    return "\n\n".join(parts), ledger
