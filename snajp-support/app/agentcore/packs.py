"""Playbooks, förvillkorsgrind och utdatakontrakt (plan Del C).

Detta är den mekanism som garanterar att en deklarerad skill faktiskt läses,
i rätt ordning, mekaniskt — inte via en prompt-önskan en modell kan hoppa
över. Tre lager av garanti:

1. Förladdning: motorn injicerar hela SKILL.md (eller en deklarerad skopa)
   i meddelandekedjan INNAN modellen kör. Motorn väljer, aldrig modellen.
2. Förvillkorsgrind: ett steg vägrar köra om något i requires[] inte redan
   är markerat som uppfyllt i körningens RunLedger — en kontrollerad
   RuntimeError, inte ett undantag som tyst faller igenom.
3. Utdatakontrakt: varje stegs svar måste innehålla sources_used[] och
   context_refs[]. Saknas en referens skillens egen mall kräver körs
   steget om en gång, sedan eskaleras det till människa.

Om ett skill-anrop misslyckas eller verkar oläst: hårdna grinden här,
rör aldrig den vendorade skillens innehåll (agent-core/skills/).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .registry import load_full_skill, load_reference, load_section, parse_skill_name


class ScopeWithoutRationaleError(ValueError):
    """INV-SKILL-003: en skopa utan motivering. Standard är hel skill."""


class MissingRequirementError(RuntimeError):
    """Förvillkorsgrinden: steget vägras köra. Inte en prompt-önskan."""


@dataclass(frozen=True)
class PlaybookStep:
    skill: str  # t.ex. "cs:ticket-triage" eller "snajp:retention-conversation"
    requires: tuple[str, ...]  # INV-SKILL-002 — aldrig tomt
    scope: tuple[str, ...] = ()  # tomt = hel skill; annars exakta referensfiler
    rationale: str | None = None
    condition: str | None = None  # t.ex. "cancellation_risk" — se support/v1 steg 6
    # Per-steg override av settings.thinking_mode. None = ärv global default.
    # Beslut 2026-08-07 (support): AV överallt UTOM vid eskaleringsbedömningen
    # — snabb respons prioriteras i livechatt, men just bedömningen "ska detta
    # till en människa?" får kosta extra latens. Leads har INGET beslut ännu
    # (mailbaserat, ingen tidspress, kvalitet är prioritet) — playbook-steg
    # där lämnas utan override tills den fullständiga jämförelsen är klar,
    # se docs/THINKING_MODE_COMPARISON.md.
    thinking: str | None = None  # "enabled" | "disabled" | None

    def __post_init__(self):
        parse_skill_name(self.skill)  # kastar direkt om oprefixerat/okänt (INV-SKILL-001)
        if self.scope and not self.rationale:
            raise ScopeWithoutRationaleError(
                f"{self.skill}: en skopa kräver en rationale i playbooken (INV-SKILL-003). "
                "Utelämnas den ska hela skillen laddas i stället."
            )
        if not self.requires:
            raise MissingRequirementError(
                f"{self.skill}: steg saknar requires[] (INV-SKILL-002)."
            )
        if self.thinking not in (None, "enabled", "disabled"):
            raise ValueError(
                f"{self.skill}: thinking måste vara None/'enabled'/'disabled', fick {self.thinking!r}."
            )

    def render(self) -> str:
        """Det playbooken injicerar för detta steg. Oskopad = hela SKILL.md.
        Skopad = exakt de deklarerade referensfilerna, aldrig något modellen
        väljer vid körning (Del C, 'Playbooken bestämmer, aldrig modellen')."""
        if not self.scope:
            return load_full_skill(self.skill)
        parts = [f"### SKOPAD LADDNING av {self.skill}\nMotivering: {self.rationale}\n"]
        for item in self.scope:
            # "§ Rubrik" = en sektion i SKILL.md (Del I: "mk:sales-enablement
            # § Objection Handling Docs"). Allt annat = en references/-fil.
            if item.startswith("§ "):
                parts.append(load_section(self.skill, item[2:]))
            else:
                parts.append(f"#### {item}\n\n{load_reference(self.skill, item)}")
        return "\n\n".join(parts)


@dataclass(frozen=True)
class Playbook:
    name: str
    steps: tuple[PlaybookStep, ...]


@dataclass
class RunLedger:
    """Vad som faktiskt injicerats/uppfyllts i den här körningen. Nycklar är
    precis det ett steg kan kräva i requires=(...): 'context_pack',
    'skill:<namn>' (satt automatiskt av run_playbook_step efter injektion),
    eller ett fritt applikationsspecifikt villkor motorn själv sätter
    (t.ex. 'tenant_config_loaded', 'prior_step_output')."""

    satisfied: set[str] = field(default_factory=set)
    step_outputs: dict[str, dict] = field(default_factory=dict)
    executed_order: list[str] = field(default_factory=list)

    def mark_satisfied(self, *keys: str) -> None:
        self.satisfied.update(keys)

    def mark_skill_injected(self, skill: str) -> None:
        self.satisfied.add(f"skill:{skill}")


def check_preconditions(step: PlaybookStep, ledger: RunLedger) -> None:
    missing = [req for req in step.requires if req not in ledger.satisfied]
    if missing:
        raise MissingRequirementError(
            f"{step.skill}: förvillkor saknas i ledgern: {missing}. Steget vägras köra."
        )


@dataclass(frozen=True)
class OutputContractResult:
    verdict: str  # "ok" | "retry" | "escalate"
    missing_refs: tuple[str, ...] = ()


def check_output_contract(
    output: dict,
    *,
    required_context_refs: tuple[str, ...],
    already_retried: bool,
) -> OutputContractResult:
    """output måste innehålla sources_used[] och context_refs[] (Del C punkt 4).
    Saknas en referens skillens mall kräver: körs om en gång, sedan eskalera."""
    if "sources_used" not in output or "context_refs" not in output:
        return OutputContractResult(
            verdict="escalate" if already_retried else "retry",
            missing_refs=("sources_used", "context_refs"),
        )
    context_refs = set(output.get("context_refs") or [])
    missing = tuple(ref for ref in required_context_refs if ref not in context_refs)
    if not missing:
        return OutputContractResult(verdict="ok")
    return OutputContractResult(
        verdict="escalate" if already_retried else "retry", missing_refs=missing
    )


def run_playbook_step(
    step: PlaybookStep,
    ledger: RunLedger,
    *,
    execute: Callable[[str], dict],
    required_context_refs: tuple[str, ...] = (),
) -> dict:
    """Kör ETT steg med grinden på båda sidor:

    - Vägrar INNAN körning om ett requires-villkor saknas i ledgern
      (MissingRequirementError — testbart utan LLM, se test_gate.py).
    - Injicerar den renderade skill-texten (hel eller skopad) och anropar
      execute() — den enda punkten som pratar med en riktig modell, injicerad
      av anroparen så detta är fullt testbart med en fejkad execute.
    - Validerar utdatakontraktet efter körning, försöker en gång till vid en
      missad referens, eskalerar annars i stället för att tyst fortsätta.
    """
    check_preconditions(step, ledger)
    rendered = step.render()
    ledger.mark_skill_injected(step.skill)
    ledger.executed_order.append(step.skill)

    output = execute(rendered)
    result = check_output_contract(
        output, required_context_refs=required_context_refs, already_retried=False
    )
    if result.verdict == "retry":
        output = execute(rendered)
        result = check_output_contract(
            output, required_context_refs=required_context_refs, already_retried=True
        )
    if result.verdict == "escalate":
        output = dict(output)
        output["escalated"] = True
        output["escalation_reason"] = (
            f"{step.skill}: saknade deklarerade referenser efter omförsök: {result.missing_refs}"
        )

    ledger.step_outputs[step.skill] = output
    return output


def run_playbook(
    playbook: Playbook,
    ledger: RunLedger,
    *,
    execute: Callable[[PlaybookStep, str], dict],
    required_context_refs_by_skill: dict[str, tuple[str, ...]] | None = None,
    should_run: Callable[[PlaybookStep, RunLedger], bool] | None = None,
) -> RunLedger:
    """Kör hela kedjan i deklarationsordning. `should_run` avgör villkorade
    steg (Del E steg 6 — snajp:retention-conversation triggas bara av en
    billig klassificerare, inte av alla ärenden)."""
    required_context_refs_by_skill = required_context_refs_by_skill or {}
    for step in playbook.steps:
        if step.condition and should_run is not None and not should_run(step, ledger):
            continue
        run_playbook_step(
            step,
            ledger,
            execute=lambda rendered, _step=step: execute(_step, rendered),
            required_context_refs=required_context_refs_by_skill.get(step.skill, ()),
        )
    return ledger
