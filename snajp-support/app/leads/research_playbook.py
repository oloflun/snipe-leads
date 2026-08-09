"""Leads Fas B (Del F): researchkedjan per prospekt.

mk:customer-research -> mk:prospecting -> sa:account-research
  -> mk:competitor-profiling -> mk:competitors (A1: dossier, sedan
     jämförelsematerial — ordningen får INTE bytas, se plan A1)
  -> mk:sales-enablement (SKOPAD: § Objection Handling Docs +
     references/objection-library.md, Del I)
  -> mk:offers (hel skill — alla 7 references, Del H)
  -> mk:ab-testing (A3: erbjudandenivå, explicit osäkerhet)

Första steget kräver context_pack (Fas A:s output) — det är precis
INV-SKILL-004 ("kontextpaketet finns före varje leads-steg") i kod.
"""

from __future__ import annotations

from ..agentcore.packs import Playbook, PlaybookStep, RunLedger, check_preconditions

# BESLUT 2026-08-10 (användaren, efter att ha läst hela jämförelsen):
# thinking AV i HELA leadsflödet. Sätts explicit per steg, inte genom att
# ärva settings.thinking_mode — supportbeslutet råkar ge samma default i
# dag, och ett leadsbeslut som tyst hänger på ett supportbeslut är inget
# beslut alls. Ändras defaulten för support ligger leads still.
#
# Grund: docs/THINKING_MODE_COMPARISON.md §8. Kort — thinking PÅ övertänkte,
# gav hackiga och robotaktiga utkast med för lite kontext, och underkände
# B2C-prospekt som i själva verket passar supportprodukten bra.
THINKING = "disabled"

RESEARCH_V1 = Playbook(
    name="leads/research-v1",
    steps=(
        PlaybookStep(skill="mk:customer-research", requires=("context_pack",), thinking=THINKING),
        PlaybookStep(
            skill="mk:prospecting", requires=("skill:mk:customer-research",), thinking=THINKING
        ),
        PlaybookStep(
            skill="sa:account-research", requires=("skill:mk:prospecting",), thinking=THINKING
        ),
        PlaybookStep(
            skill="mk:competitor-profiling",
            requires=("skill:sa:account-research",),
            thinking=THINKING,
        ),
        # A1: competitor-profiling FÖRE competitors — dossiern som competitors sedan formar.
        PlaybookStep(
            skill="mk:competitors",
            requires=("skill:mk:competitor-profiling",),
            thinking=THINKING,
        ),
        PlaybookStep(
            skill="mk:sales-enablement",
            requires=("skill:mk:competitors",),
            scope=("§ Objection Handling Docs", "references/objection-library.md"),
            rationale=(
                "Kall e-post behöver invändningar, inte pitchdeck eller demoskript "
                "(Del I) — hela skillen späder en modell som då börjar föreslå "
                "ROI-kalkylatorer och demoskript i ett kallt mejl."
            ),
            thinking=THINKING,
        ),
        PlaybookStep(
            skill="mk:offers", requires=("skill:mk:sales-enablement",), thinking=THINKING
        ),
        PlaybookStep(skill="mk:ab-testing", requires=("skill:mk:offers",), thinking=THINKING),
    ),
)

_HEADER = """Du researchar ett enskilt prospekt åt {tenant_name}. Nedan följer,
i bestämd ordning, de skills som styr researcharbetet. mk:prospecting §
Quality Checks och compliance-regel 3 är HÅRDA GRINDAR i kod (se
app/leads/prospect_quality_gate.py och provenance_gate.py) — inte
rekommendationer du kan välja att skippa.

{context_pack}
"""


def render_research_instructions(*, tenant_name: str, context_pack: str) -> tuple[str, RunLedger]:
    """Bygger instruktionstexten för Fas B genom förvillkorsgrinden.
    Returnerar (instruktionstext, ledger)."""
    ledger = RunLedger(satisfied={"context_pack"})
    parts: list[str] = [_HEADER.format(tenant_name=tenant_name, context_pack=context_pack)]

    for step in RESEARCH_V1.steps:
        check_preconditions(step, ledger)
        rendered = step.render()
        ledger.mark_skill_injected(step.skill)
        ledger.executed_order.append(step.skill)
        parts.append(f"---\n### Skill: {step.skill}\n{rendered}")

    return "\n\n".join(parts), ledger
