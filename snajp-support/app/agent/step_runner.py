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

from ..agentcore.instruktioner import Instruktionslager, las_instruktioner  # noqa: F401
from ..agentcore.overlays import load_global_instructions as load_global_instructions_fil
from ..agentcore.overlays import load_overlay
from ..agentcore.packs import PlaybookStep, RunLedger, check_output_contract, check_preconditions
from ..config import get_settings
from .llm import get_llm_client

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
    # Kundlagret (agent_configs.instructions_md, migration 049). Utan de
    # här två går det inte att skilja "kunden har inga instruktioner" från
    # "kundens instruktioner nådde inte prompten" — och det var precis den
    # skillnaden som inte gick att se när fältet var dött.
    kund_chars: int = 0
    instruktionshash: str = ""
    # Vad modellen faktiskt FICK. Utan de här kan spårvyn visa skillnamn,
    # tokens och latens men inte svara på "varför skrev den så här?" — och
    # skill-texten är fritt redigerbar, så namnet ensamt räcker inte
    # (INV-AUDIT-001, migration 027).
    system_prompt: str = ""
    user_message: str = ""


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

    #: Kapning per fält i step_log. Räcker till felsökning; hela prompten är
    #: sällan det man läser, och en spårvy som drar 200 kB per rad är en
    #: spårvy ingen öppnar.
    #: ponytail: 8k per fält; flytta till objektlagring om vi behöver mer.
    TRACE_FIELD_MAX_CHARS = 8_000

    def as_log(self, *, verbose: bool = True) -> list[dict[str, Any]]:
        """Det som skrivs till agent_runs.step_log.

        `verbose` styrs av agent_configs.settings.trace_verbose och är PÅ som
        default: vi är i pilotfas och behöver spåret mer än vi behöver
        diskutrymmet. Utan det innehåller loggen mätvärden men ingen text,
        vilket räcker för att se ATT ett steg gick fel och inte för att se
        varför."""
        def _cap(value: str | None) -> str | None:
            if value is None:
                return None
            return value[: RunTrace.TRACE_FIELD_MAX_CHARS]

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
                "kund_chars": s.kund_chars,
                "instruktionshash": s.instruktionshash[:12],
                "sources_used": s.output.get("sources_used", []),
                "context_refs": s.output.get("context_refs", []),
                **(
                    {
                        "system_prompt": _cap(s.system_prompt),
                        "user_message": _cap(s.user_message),
                        "raw_output": _cap(
                            json.dumps(s.output, ensure_ascii=False) if s.output else ""
                        ),
                        "reasoning_content": _cap(s.reasoning_content),
                    }
                    if verbose
                    else {}
                ),
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
    instruktioner: Instruktionslager | None = None,
) -> dict[str, Any]:
    """Kör ETT skill-steg som ett eget LLM-anrop.

    Förvillkorsgrinden körs FÖRE anropet (kastar MissingRequirementError om
    ett requires[] saknas i ledgern) — inget anrop görs då alls.

    `instruktioner` hämtas EN gång per körning av anroparen (se
    agentcore/instruktioner.las_instruktioner) och skickas hit. Att varje steg
    läser databasen själv hade betytt ett dussin läsningar per ärende och —
    värre — att ett sparande mitt i en körning kan ge steg 1 och steg 8 olika
    regler. Utelämnas den faller den tillbaka på agent-core/AGENTS.md, vilket
    är beteendet före migration 049.
    """
    check_preconditions(step, ledger)

    settings = get_settings()
    client = get_llm_client()
    skill_text = step.render()

    # Systempromptens ordning är inte godtycklig:
    #   1. GLOBALT     — mest generell policy, så skill/overlay kan specialisera
    #   2. skill_text  — den vendorade metodiken
    #   3. overlay     — vår specialisering per STEG; "senare vinner vid
    #                    konflikt", och delimitertexten säger det explicit
    #   4. KUND        — vår specialisering per KUND, alltså den mest specifika
    #                    av våra nivåer och därför sist av instruktionerna
    #   5. kontraktet  — SIST och ovillkorligt. Läggs på av kod som varken en
    #                    overlay, en kundinstruktion eller en SOUL kan nå, så
    #                    utdatakontraktet inte kan försvagas av tuninglagren.
    # ALLT här är VÅR text — inklusive kundlagret, som är admin-only. KUNDSKRIVEN
    # text (SOUL, affärskontext, kunskapsbas) går i user-position, aldrig här.
    # Den skillnaden ÄR säkerhetsgränsen; se app/leads/soul.py och
    # app/agentcore/instruktioner.py.
    lager = instruktioner or Instruktionslager(
        global_md=load_global_instructions_fil(), kund_md=""
    )
    # Flera overlays renderas i deklarationsordning, var och en med sin egen
    # avgränsare — "senare vinner vid konflikt" gäller alltså även MELLAN
    # overlays, så ett stegs syftesoverlay kan specialisera de hårda reglerna.
    overlay_texts = [(namn, load_overlay(namn)) for namn in step.overlay_names]
    overlay_chars_total = sum(len(text) for _, text in overlay_texts)
    overlay_label = "+".join(namn for namn, _ in overlay_texts) or None

    system_parts: list[str] = []
    if lager.global_block:
        system_parts.append(lager.global_block)
    system_parts.append(
        f"Du utför ETT steg i {playbook_role}. Steget styrs av "
        f"skillen {step.skill}, vars fullständiga innehåll följer nedan. Följ "
        f"den. Uppfinn aldrig fakta.\n\n{skill_text}"
    )
    for namn, overlay_text in overlay_texts:
        system_parts.append(
            f"{_OVERLAY_OPEN.format(name=namn)}\n{overlay_text}\n{_OVERLAY_CLOSE}"
        )
    if lager.kund_block:
        system_parts.append(lager.kund_block)
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

    # Formuleringssteg (humanizer, utkast) får deklarera en varmare temperatur
    # i playbooken; analys- och bedömningssteg ärver den kalla defaulten.
    # Transportfel (timeout, 429, 5xx) hanteras av AsyncOpenAI-klientens egna
    # omtag med exponentiell backoff — se get_llm_client i agent/llm.py.
    effective_temperature = step.temperature if step.temperature is not None else 0.3

    for attempt in (1, 2):
        response = await client.chat.completions.create(
            model=settings.model,
            response_format={"type": "json_object"},
            temperature=effective_temperature,
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
            overlay=overlay_label,
            overlay_chars=overlay_chars_total,
            global_chars=len(lager.global_md),
            kund_chars=len(lager.kund_md),
            instruktionshash=lager.hash,
            # messages[0]/[1] är systemprompten och användarmeddelandet SOM DE
            # SÅG UT VID FÖRSTA ANROPET. Eventuella omförsök lägger till fler
            # meddelanden i listan, men det är den första uppsättningen som
            # svarar på "vad bad vi om".
            system_prompt=messages[0]["content"],
            user_message=messages[1]["content"],
        )
    )
    return output
