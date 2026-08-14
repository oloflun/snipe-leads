"""Leads Fas C (Del F): outreach.

sa:draft-outreach + mk:cold-email/references/personalization.md  (skapa)
  -> mk:cold-email/SKILL.md                                       (granska)
  -> snajp:humanizer-svenska                                      (ALLTID sist)

sa:draft-outreach producerar som standard även LinkedIn-kopia ("Copy for
LinkedIn (always)", SKILL.md rad 40). Den utdatan stängs av här — krockar
med LinkedIn-policyn i G4 (proveniensgrinden tillåter LinkedIn bara som
verifiering, aldrig som kanal). Vi använder e-postvägen. sa:draft-outreach
kräver självt "No markdown formatting" (rad 291) — samma gate som
cs:draft-response (app/agent/tools.strip_markdown) tillämpas här också,
humanizern får inte återinföra formatering.
"""

from __future__ import annotations

from ..agent.tools import strip_markdown
from ..agentcore.packs import Playbook, PlaybookStep, RunLedger, check_preconditions

# thinking AV i hela leadsflödet — se research_playbook.THINKING för beslutet.
from .research_playbook import THINKING  # noqa: E402

# De hårda reglerna (LinkedIn-förbudet, ren text, språkläget) låg tidigare som
# en f-sträng mitt i leads_agent.run_outreach_draft, alltså i USER-position och
# på ett ställe ingen letade. Nu är de en overlay i SYSTEM-position: samma text,
# starkare placering, och versionerad via overlay_hash i pack_version.
_HARD_RULES = "leads-hard-rules"

OUTREACH_V1 = Playbook(
    name="leads/outreach-v1",
    steps=(
        PlaybookStep(
            skill="sa:draft-outreach",
            requires=("offer_selected",),
            overlay=_HARD_RULES,
            thinking=THINKING,
        ),
        PlaybookStep(
            skill="mk:cold-email",
            requires=("skill:sa:draft-outreach",),
            scope=("references/personalization.md",),
            rationale="Skapandesteget behöver personaliseringssignaler, inte hela mk:cold-email-metodiken än.",
            overlay=_HARD_RULES,
            thinking=THINKING,
        ),
        # granska: hel skill
        PlaybookStep(
            skill="mk:cold-email",
            requires=("skill:mk:cold-email",),
            overlay=_HARD_RULES,
            thinking=THINKING,
        ),
        PlaybookStep(
            skill="snajp:humanizer-svenska",
            requires=("skill:mk:cold-email",),
            overlay=_HARD_RULES,
            thinking=THINKING,
        ),
    ),
)

_HEADER = """Du skriver ett kallt utskick till {company_name} åt {tenant_name}.
Nedan följer, i bestämd ordning, de skills som styr arbetet.

VIKTIGT — åsidosätter sa:draft-outreach:s standardbeteende (G4): producera
ALDRIG LinkedIn-kopia eller ett LinkedIn-anslutningsmeddelande, oavsett vad
skillen nedan säger om att alltid inkludera det. E-postvägen är den enda
kanalen. Om ingen verifierad e-post finns: eskalera, föreslå inte LinkedIn
som fallback.

Ren text, aldrig markdown (sa:draft-outreach är redan explicit om detta) —
humanizern får inte återinföra asterisker, fetstil eller punktlistor.

Erbjudande som styr vinkeln: {offer_summary}
{context_pack}
"""


def render_outreach_instructions(
    *, tenant_name: str, company_name: str, offer_summary: str, context_pack: str
) -> tuple[str, RunLedger]:
    ledger = RunLedger(satisfied={"offer_selected", "context_pack"})
    parts: list[str] = [
        _HEADER.format(
            tenant_name=tenant_name,
            company_name=company_name,
            offer_summary=offer_summary,
            context_pack=context_pack,
        )
    ]
    for step in OUTREACH_V1.steps:
        check_preconditions(step, ledger)
        rendered = step.render()
        ledger.mark_skill_injected(step.skill)
        ledger.executed_order.append(step.skill)
        parts.append(f"---\n### Skill: {step.skill}\n{rendered}")
    return "\n\n".join(parts), ledger


def finalize_outreach_body(draft: str) -> str:
    """Samma markdown-grind som cs:draft-response (app/agent/tools.py) —
    sa:draft-outreach kräver plain text lika explicit ('Never use asterisks,
    bold, or other markdown', SKILL.md rad 291). Humanizern får inte
    återinföra formatering; det här är kodgrinden som garanterar det
    oavsett vad modellen faktiskt skrev, samma princip som hela Del C."""
    return strip_markdown(draft)
