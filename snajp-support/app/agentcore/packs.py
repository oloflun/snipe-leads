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

from .registry import load_full_skill, load_reference, load_section, load_skill_md, parse_skill_name


class ScopeWithoutRationaleError(ValueError):
    """INV-SKILL-003: en skopa utan motivering. Standard är hel skill."""


class RadandringSaknasError(ValueError):
    """En textändring pekar på text som inte finns i den lästa skillen."""


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
    # Per-steg temperatur. None = step_runners default (0.3). Sätts högre bara
    # på steg vars uppgift ÄR formulering (humaniseraren, utkastet) — analys-
    # och bedömningssteg ska förbli kalla. Beslut 2026-08-25: 0.3 för allt gav
    # svar som återanvände samma fraser ordagrant mellan ärenden.
    temperature: float | None = None
    # Den sanktionerade finjusteringsytan (INV-SKILL-005: "justera med
    # tilläggsinstruktioner ovanpå skillen, aldrig i skillen"). Namn på en fil
    # i agent-core/overlays/ — eller en TUPLE av namn, injicerade i ordning —
    # i SYSTEMposition efter skill-texten. Fritt redigerbar, versionerad via
    # overlays.overlay_hash() i pack_version.
    # Behöver du ändra vad ett steg säger: gör det här, inte i skillen.
    #
    # Komposition (2026-08-26): ett steg som behöver BÅDE de hårda reglerna
    # och en syftesoverlay (svar, uppföljning) anger båda. Alternativet var
    # att duplicera hårdreglerna in i varje syftesoverlay — och duplicerad
    # tuning divergerar, vilket är exakt det overlays finns för att undvika.
    overlay: str | tuple[str, ...] | None = None
    # Per-steg-modellval (2026-09-02, vägen till 0,10 kr/lead): namnet på
    # ett Settings-FÄLT (t.ex. "leads_draft_model") vars värde, om satt,
    # ersätter settings.model för just det här stegets anrop. Ett fältnamn
    # och inte en modellsträng: modellvalet ska kunna flippas per miljö via
    # env utan omdeploy av kod, och playbooks är frusna vid import. Tomt
    # fältvärde vid körning = ärv settings.model. Opt-in med default None —
    # inga befintliga playbooks påverkas.
    model_setting: str | None = None
    # V2-kostnadsarbetet (2026-09-02): FLER skills i SAMMA steg/anrop. Varje
    # post är (skillnamn, skopa) där tom skopa = hel skill och en icke-tom
    # skopa följer samma "§ Rubrik"/references-form som `scope` ovan.
    # Renderas EFTER huvudskillen, i deklarationsordning, var och en under
    # sin egen rubrik. Opt-in med default () — inga befintliga playbooks
    # påverkas. Injektionsgarantin är densamma: motorn renderar texten före
    # anropet, modellen väljer aldrig. En skopad extra-skill kräver att
    # STEGET bär en rationale (INV-SKILL-003 gäller även här).
    extra_skills: tuple[tuple[str, tuple[str, ...]], ...] = ()
    # Textändringar i den lästa skilltexten (2026-10-06): (exakt text ur
    # skillen, ersättning, skäl). Tom ersättning stryker texten. Skillfilen
    # rörs aldrig (INV-SKILL-005); ändringen sker på texten efter läsningen,
    # står här i playbooken med sitt skäl och syns i spåret. Behövdes när en
    # enda rad i en annars användbar sektion fick fel effekt: sa:draft-outreachs
    # "[Brief proof: We helped [Similar Company] achieve [Result]]" gav ett
    # påhittat case i ett svenskt kallmejl, och att skopa bort hela sektionen
    # hade tagit arbetsflödet och exemplet med sig. Finns texten inte i skillen
    # (efter en ny vendoring) faller importen: en ändring kan aldrig tyst sluta
    # gälla.
    radandringar: tuple[tuple[str, str, str], ...] = ()

    @property
    def overlay_names(self) -> tuple[str, ...]:
        """Overlayerna som tuple, oavsett hur fältet deklarerades."""
        if not self.overlay:
            return ()
        if isinstance(self.overlay, str):
            return (self.overlay,)
        return self.overlay

    def __post_init__(self):
        parse_skill_name(self.skill)  # kastar direkt om oprefixerat/okänt (INV-SKILL-001)
        for namn in self.overlay_names:
            # Samma fail-fast som skill-namnet: ett felstavat overlay-namn
            # fäller modulimporten, alltså CI, aldrig först i produktion.
            from .overlays import parse_overlay_name

            parse_overlay_name(namn)
        if self.scope and not self.rationale:
            raise ScopeWithoutRationaleError(
                f"{self.skill}: en skopa kräver en rationale i playbooken (INV-SKILL-003). "
                "Utelämnas den ska hela skillen laddas i stället."
            )
        for extra_namn, extra_skopa in self.extra_skills:
            parse_skill_name(extra_namn)  # samma fail-fast som huvudskillen
            if extra_skopa and not self.rationale:
                raise ScopeWithoutRationaleError(
                    f"{self.skill}: extra-skillen {extra_namn} är skopad — steget "
                    "måste bära en rationale (INV-SKILL-003)."
                )
        if not self.requires:
            raise MissingRequirementError(
                f"{self.skill}: steg saknar requires[] (INV-SKILL-002)."
            )
        if self.thinking not in (None, "enabled", "disabled"):
            raise ValueError(
                f"{self.skill}: thinking måste vara None/'enabled'/'disabled', fick {self.thinking!r}."
            )
        if self.radandringar:
            lasta = self._rendera_last()
            for gammal, _ny, skal in self.radandringar:
                if not skal.strip():
                    raise ScopeWithoutRationaleError(
                        f"{self.skill}: en textändring kräver ett skäl (INV-SKILL-003)."
                    )
                if not gammal or gammal not in lasta:
                    raise RadandringSaknasError(
                        f"{self.skill}: texten som ska ändras finns inte i den lästa skillen "
                        f"(ny vendoring?): {gammal[:80]!r}"
                    )

    @staticmethod
    def _render_scoped(skill: str, scope: tuple[str, ...], rationale: str | None) -> str:
        parts = [f"### SKOPAD LADDNING av {skill}\nMotivering: {rationale}\n"]
        for item in scope:
            # "§ Rubrik" = en sektion i SKILL.md (Del I: "mk:sales-enablement
            # § Objection Handling Docs"). Allt annat = en references/-fil.
            if item.startswith("§ "):
                parts.append(load_section(skill, item[2:]))
            else:
                parts.append(f"#### {item}\n\n{load_reference(skill, item)}")
        return "\n\n".join(parts)

    def render(self) -> str:
        """Det playbooken injicerar för detta steg. Oskopad = hela SKILL.md.
        Skopad = exakt de deklarerade referensfilerna, aldrig något modellen
        väljer vid körning (Del C, 'Playbooken bestämmer, aldrig modellen').
        Deklarerade extra_skills renderas EFTER huvudskillen, var och en
        under sin egen rubrik — samma motor-injektionsgaranti. Textändringarna
        (`radandringar`) tillämpas sist."""
        text = self._rendera_last()
        for gammal, ny, _skal in self.radandringar:
            text = text.replace(gammal, ny)
        return text

    def lasta_delar(self) -> list[dict[str, object]]:
        """Filerna och sektionerna steget läser, i den ordning de renderas.

        Insynens utfällning av skill-lagret (Fas 7). Följer _rendera_last gren
        för gren — hel skill = SKILL.md + references/, skopa = exakt de
        deklarerade posterna — och läser texten med samma funktioner, så
        teckenantalen är de som faktiskt hamnar i prompten. Varje post bär
        kontrollen mot manifestet (registry.fil_kontroll)."""
        from .registry import fil_kontroll, reference_files

        delar: list[dict[str, object]] = []

        def _skill(namn: str, skopa: tuple[str, ...]) -> None:
            poster = skopa or ("SKILL.md", *reference_files(namn))
            for post in poster:
                if post.startswith("§ "):
                    fil, text = "SKILL.md", load_section(namn, post[2:])
                elif post == "SKILL.md":
                    fil, text = post, load_skill_md(namn)
                else:
                    fil, text = post, load_reference(namn, post)
                delar.append(
                    {"skill": namn, "del": post, "fil": fil, "tecken": len(text), **fil_kontroll(namn, fil)}
                )

        _skill(self.skill, self.scope)
        for extra_namn, extra_skopa in self.extra_skills:
            _skill(extra_namn, extra_skopa)
        return delar

    def _rendera_last(self) -> str:
        """Skilltexten exakt som den läses, före textändringarna."""
        if not self.scope:
            rendered = load_full_skill(self.skill)
        else:
            rendered = self._render_scoped(self.skill, self.scope, self.rationale)
        for extra_namn, extra_skopa in self.extra_skills:
            if extra_skopa:
                extra_text = self._render_scoped(extra_namn, extra_skopa, self.rationale)
            else:
                extra_text = load_full_skill(extra_namn)
            rendered += f"\n\n---\n### Skill (i samma steg): {extra_namn}\n{extra_text}"
        return rendered


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
