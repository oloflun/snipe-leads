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

# Temperaturerna speglar supportbeslutet 2026-08-25: 0.3 på allt gav svar som
# återanvände samma fraser ordagrant mellan ärenden, så FORMULERINGSSTEG fick
# 0.5 (utkast) och 0.7 (humanizer) medan analys- och bedömningssteg behöll den
# kalla defaulten. Leads-kedjan fick aldrig samma justering — utkastet och
# humaniseraren var de kallaste stegen i just den kedja vars hela uppgift är
# formulering, och 2026-08-09-utkastens likformighet ("supportagenten",
# "returfrågor" som ämnesrader) är precis det symptomet. Granskningssteget
# (mk:cold-email hel) förblir kallt: det BEDÖMER, det formulerar inte.
OUTREACH_V1 = Playbook(
    name="leads/outreach-v1",
    steps=(
        PlaybookStep(
            skill="sa:draft-outreach",
            requires=("offer_selected",),
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.5,
        ),
        PlaybookStep(
            skill="mk:cold-email",
            requires=("skill:sa:draft-outreach",),
            scope=("references/personalization.md",),
            rationale="Skapandesteget behöver personaliseringssignaler, inte hela mk:cold-email-metodiken än.",
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.5,
        ),
        # granska: hel skill — bedömning, inte formulering; kall default.
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
            temperature=0.7,
        ),
    ),
)

# V2 (2026-09-02, kostnadsarbetet): 4 anrop -> 2, med SAMMA skillinnehåll.
#
# Steg 1 slår ihop V1:s skapa+personalisera+granska till ETT anrop:
# sa:draft-outreach (hel) + mk:cold-email via extra_skills i SAMMA steg —
# personaliseringsreferensen och granskningschecklistan (§ Quality Check +
# § What to Avoid, sektionerna som utgör själva granskningen i SKILL.md).
# Skilltexterna är alltså DESAMMA som V1 injicerade, i ett anrop i stället
# för tre — "ersätt workflowen, inte skillsen".
#
# Steg 2 är humanizern, oförändrat HEL och oförändrat SIST: INV-LANG-002
# (humanizern måste vara den som rörde texten sist) bevaras strukturellt
# utan invariantändring. Grundningscykeln (villkorad, max 1 runda) och
# tomtext-omförsöket behålls exakt — se run_outreach_draft_v2 i
# app/agent/leads_research_v2.py.
OUTREACH_V2 = Playbook(
    name="leads/outreach-v2",
    steps=(
        PlaybookStep(
            skill="sa:draft-outreach",
            requires=("offer_selected",),
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.5,
            rationale=(
                "V2-kostnadsarbetet: mk:cold-email skopas till personaliserings-"
                "referensen + granskningssektionerna (Quality Check, What to "
                "Avoid) — resten av skillen är metodik för kampanjer och "
                "uppföljningssekvenser som det här steget inte utför."
            ),
            extra_skills=(
                (
                    "mk:cold-email",
                    (
                        "references/personalization.md",
                        "§ Quality Check",
                        "§ What to Avoid",
                    ),
                ),
            ),
        ),
        PlaybookStep(
            skill="snajp:humanizer-svenska",
            requires=("skill:sa:draft-outreach",),
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.7,
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
