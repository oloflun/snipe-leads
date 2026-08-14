"""Ett LLM-anrop PER skill-steg (Del C p.2+4) — inte en hopklistrad prompt.

Varför det här finns: tidigare konkatenerades alla sju cs:-skills till EN
systemprompt i EN agentloop. Då gick det inte att observera vilka skills som
faktiskt användes, och "läsgarantin" var overifierbar i praktiken —
förvillkorsgrinden bevisade bara injektionsORDNING vid bygget.

Nu kör varje steg som ett eget anrop i JSON-läge med ett eget utdatakontrakt.
Det ger tre saker planen kräver men som saknades:
  1. sources_used[] / context_refs[] per steg, faktiskt validerat (Del C p.4)
  2. en verklig, loggbar spårning av vilket steg som gjorde vad
  3. omkörning en gång vid brutet kontrakt, sedan eskalering — i stället för
     att tyst fortsätta

Sidoeffekter (skapa ärende, spara meddelande, eskalera) görs ALDRIG av ett
steg här — de görs i kod av anroparen. Modellen resonerar; koden agerar.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from ..agentcore.overlays import load_global_instructions, load_overlay
from ..agentcore.packs import PlaybookStep, RunLedger, check_output_contract, check_preconditions
from ..config import get_settings
from .llm import get_llm_client

_GLOBAL_OPEN = """## GLOBALA REGLER (Snajp — gäller varje steg, varje kund)
Dessa gäller ÖVER skillen nedan där de krockar. De är policy, inte stil.
"""
_GLOBAL_CLOSE = "## SLUT GLOBALA REGLER"

_OVERLAY_OPEN = """## TILLÄGGSINSTRUKTIONER (Snajp-overlay: {name})
Dessa kommer FRÅN OSS, inte från skillen ovan, och gäller ÖVER den där de
krockar. De ersätter aldrig kodgrindarna — grindarna körs efter dig.
"""
_OVERLAY_CLOSE = "## SLUT TILLÄGGSINSTRUKTIONER"

_CONTRACT_INSTRUCTION = """
Svara ENBART med ett JSON-objekt. Utöver de fält uppgiften kräver MÅSTE du
alltid inkludera:
  "sources_used": [...]   // vad du faktiskt grundade svaret i (KB-titlar,
                          // tidigare stegs utdata, kontextpaketet). Tom lista
                          // om du inte hade något underlag.
  "context_refs": [...]   // vilka av de tillhandahållna referenserna du använde
Ljug inte i dessa fält — de kontrolleras maskinellt.
"""


def thinking_kwargs(mode: str) -> dict[str, Any]:
    """DeepSeek v4:s thinking-toggle. Verifierat empiriskt mot API:t:
    `{'thinking': {'type': 'disabled'}}` stänger av reasoning_content helt
    (usage.completion_tokens_details blir None). `reasoning_effort='none'`
    är OpenAI-kompatibilitetsaliaset och ger samma resultat.

    Gäller bara DeepSeek — skickas inte till andra providers.
    """
    if mode == "disabled":
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    return {}


@dataclass
class StepResult:
    skill: str
    output: dict[str, Any]
    attempts: int
    escalated: bool
    escalation_reason: str | None
    latency_ms: int
    tokens_in: int
    tokens_out: int
    reasoning_tokens: int = 0
    reasoning_content: str | None = None
    # Bevis på att HELA skillen injicerades (SKILL.md + references/), inte
    # bara en rubrik — se agentcore/registry.load_full_skill.
    injected_chars: int = 0
    thinking_mode: str = "disabled"
    # Vilken overlay som formade steget, och hur mycket text den bidrog med.
    # Utan detta i revisionsloggen går det inte att svara på "varför skrev den
    # så här?" — skill-namnet ensamt räcker inte när tuninglagret är fritt
    # redigerbart (INV-AUDIT-001).
    overlay: str | None = None
    overlay_chars: int = 0
    global_chars: int = 0


@dataclass
class RunTrace:
    """Den observerbara loggen över vad som faktiskt hände, steg för steg.
    Skrivs till agent_runs (G10) och returneras till API-anroparen."""

    steps: list[StepResult] = field(default_factory=list)

    @property
    def skills_used(self) -> list[str]:
        return [s.skill for s in self.steps]

    @property
    def total_tokens_in(self) -> int:
        return sum(s.tokens_in for s in self.steps)

    @property
    def total_tokens_out(self) -> int:
        return sum(s.tokens_out for s in self.steps)

    @property
    def total_reasoning_tokens(self) -> int:
        return sum(s.reasoning_tokens for s in self.steps)

    def as_log(self) -> list[dict[str, Any]]:
        return [
            {
                "skill": s.skill,
                "attempts": s.attempts,
                "escalated": s.escalated,
                "escalation_reason": s.escalation_reason,
                "latency_ms": s.latency_ms,
                "tokens_in": s.tokens_in,
                "tokens_out": s.tokens_out,
                "reasoning_tokens": s.reasoning_tokens,
                "injected_chars": s.injected_chars,
                "thinking_mode": s.thinking_mode,
                "overlay": s.overlay,
                "overlay_chars": s.overlay_chars,
                "global_chars": s.global_chars,
                "sources_used": s.output.get("sources_used", []),
                "context_refs": s.output.get("context_refs", []),
            }
            for s in self.steps
        ]

    def as_full(self) -> list[dict[str, Any]]:
        """Som as_log(), plus HELA stegets utdata och dess reasoning_content.
        Går till API-anroparen/rapporten, inte till agent_runs.step_log —
        DB-loggen ska vara granskbar, inte en andra kopia av allt innehåll."""
        return [
            {
                **entry,
                "output": step.output,
                "reasoning_content": step.reasoning_content,
            }
            for entry, step in zip(self.as_log(), self.steps)
        ]


async def run_step(
    step: PlaybookStep,
    ledger: RunLedger,
    trace: RunTrace,
    *,
    task: str,
    case_context: str,
    required_context_refs: tuple[str, ...] = (),
    playbook_role: str = "en svensk kundtjänst-playbook",
) -> dict[str, Any]:
    """Kör ETT skill-steg som ett eget LLM-anrop.

    Förvillkorsgrinden körs FÖRE anropet (kastar MissingRequirementError om
    ett requires[] saknas i ledgern) — inget anrop görs då alls.
    """
    check_preconditions(step, ledger)

    settings = get_settings()
    client = get_llm_client()
    skill_text = step.render()

    # Systempromptens ordning är inte godtycklig:
    #   1. AGENTS.md   — mest generell policy, så skill/overlay kan specialisera
    #   2. skill_text  — den vendorade metodiken
    #   3. overlay     — vår specialisering; "senare vinner vid konflikt", och
    #                    delimitertexten säger det explicit
    #   4. kontraktet  — SIST och ovillkorligt. Läggs på av kod som varken en
    #                    overlay eller en SOUL kan nå, så utdatakontraktet inte
    #                    kan försvagas av något av tuninglagren.
    # ALLT här är VÅR text. Kundskriven text (SOUL) går i user-position, aldrig
    # här — den skillnaden ÄR säkerhetsgränsen, se app/leads/soul.py.
    global_text = load_global_instructions()
    overlay_text = load_overlay(step.overlay) if step.overlay else ""

    system_parts: list[str] = []
    if global_text:
        system_parts.append(f"{_GLOBAL_OPEN}\n{global_text}\n{_GLOBAL_CLOSE}")
    system_parts.append(
        f"Du utför ETT steg i {playbook_role}. Steget styrs av "
        f"skillen {step.skill}, vars fullständiga innehåll följer nedan. Följ "
        f"den. Uppfinn aldrig fakta.\n\n{skill_text}"
    )
    if overlay_text:
        system_parts.append(
            f"{_OVERLAY_OPEN.format(name=step.overlay)}\n{overlay_text}\n{_OVERLAY_CLOSE}"
        )
    system_parts.append(_CONTRACT_INSTRUCTION)

    messages = [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": f"{case_context}\n\n## Din uppgift i det här steget\n{task}"},
    ]

    output: dict[str, Any] = {}
    tokens_in = tokens_out = reasoning_tokens = 0
    reasoning_content: str | None = None
    started = time.monotonic()
    # Steget vinner över den globala defaulten om det deklarerar en egen
    # thinking-nivå (t.ex. cs:customer-escalation, se support_playbook.py).
    effective_mode = step.thinking if step.thinking is not None else settings.thinking_mode
    extra = thinking_kwargs(effective_mode) if settings.llm_provider == "deepseek" else {}

    for attempt in (1, 2):
        response = await client.chat.completions.create(
            model=settings.model,
            response_format={"type": "json_object"},
            temperature=0.3,
            messages=messages,
            **extra,
        )
        usage = getattr(response, "usage", None)
        if usage:
            tokens_in += getattr(usage, "prompt_tokens", 0) or 0
            tokens_out += getattr(usage, "completion_tokens", 0) or 0
            details = getattr(usage, "completion_tokens_details", None)
            if details:
                reasoning_tokens += getattr(details, "reasoning_tokens", 0) or 0
        choice_message = response.choices[0].message
        reasoning_content = getattr(choice_message, "reasoning_content", None) or reasoning_content
        try:
            output = json.loads(choice_message.content or "{}")
        except json.JSONDecodeError:
            output = {}

        verdict = check_output_contract(
            output,
            required_context_refs=required_context_refs,
            already_retried=(attempt == 2),
        )
        if verdict.verdict == "ok":
            break
        if verdict.verdict == "escalate":
            break
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Ditt svar saknade obligatoriska fält/referenser: {verdict.missing_refs}. "
                    "Svara igen, med hela kontraktet uppfyllt."
                ),
            }
        )

    latency_ms = int((time.monotonic() - started) * 1000)
    escalated = verdict.verdict == "escalate"
    reason = (
        f"{step.skill}: utdatakontraktet uppfylldes inte efter omförsök "
        f"(saknade {verdict.missing_refs})"
        if escalated
        else None
    )

    ledger.mark_skill_injected(step.skill)
    ledger.executed_order.append(step.skill)
    ledger.step_outputs[step.skill] = output
    trace.steps.append(
        StepResult(
            skill=step.skill,
            output=output,
            attempts=attempt,
            escalated=escalated,
            escalation_reason=reason,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            reasoning_tokens=reasoning_tokens,
            reasoning_content=reasoning_content,
            injected_chars=len(skill_text),
            thinking_mode=effective_mode,
            overlay=step.overlay,
            overlay_chars=len(overlay_text),
            global_chars=len(global_text),
        )
    )
    return output
