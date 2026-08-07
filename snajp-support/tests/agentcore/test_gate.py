"""Förvillkorsgrind + utdatakontrakt (Del C punkt 3-4) — den mekanism som
garanterar att ett deklarerat skill-steg faktiskt injiceras och läses, i
ordning, istället för att modellen kan hoppa över det. Detta är läsgarantins
kärntest: 'ett steg vägrar köra i stället för att köra utan' (plan,
Verifiering)."""

from __future__ import annotations

import pytest

from app.agentcore.packs import (
    MissingRequirementError,
    Playbook,
    PlaybookStep,
    RunLedger,
    check_output_contract,
    check_preconditions,
    run_playbook,
    run_playbook_step,
)


def _valid_output(**extra):
    return {"sources_used": ["kb-artikel-1"], "context_refs": ["context_pack"], **extra}


# -- Förvillkorsgrinden: kontextpaketet saknas -> steget vägrar köra --------


def test_precondition_gate_refuses_when_context_pack_missing():
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    ledger = RunLedger()  # tomt — inget är injicerat än
    with pytest.raises(MissingRequirementError):
        check_preconditions(step, ledger)


def test_precondition_gate_allows_when_satisfied():
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    ledger = RunLedger(satisfied={"context_pack"})
    check_preconditions(step, ledger)  # kastar inte


def test_run_playbook_step_refuses_before_calling_execute():
    """Grinden stoppar FÖRE modellanropet — execute() ska aldrig nås."""
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    ledger = RunLedger()
    calls = []

    def execute(rendered: str) -> dict:
        calls.append(rendered)
        return _valid_output()

    with pytest.raises(MissingRequirementError):
        run_playbook_step(step, ledger, execute=execute)
    assert calls == [], "execute() anropades trots saknat förvillkor — grinden läckte."


def test_run_playbook_step_depends_on_a_prior_step_being_injected():
    """requires=('skill:cs:ticket-triage',) uppfylls bara om det steget
    faktiskt kört och injicerats — inte av att man bara säger att det gjort det."""
    dependent = PlaybookStep(skill="cs:customer-research", requires=("skill:cs:ticket-triage",))
    ledger = RunLedger()  # ticket-triage har INTE kört
    with pytest.raises(MissingRequirementError):
        run_playbook_step(dependent, ledger, execute=lambda rendered: _valid_output())

    # Kör triage först — nu ska customer-research kunna köra.
    triage = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    ledger2 = RunLedger(satisfied={"context_pack"})
    run_playbook_step(triage, ledger2, execute=lambda rendered: _valid_output())
    run_playbook_step(dependent, ledger2, execute=lambda rendered: _valid_output())  # kastar inte
    assert ledger2.executed_order == ["cs:ticket-triage", "cs:customer-research"]


# -- Utdatakontraktet: saknad context_ref -> ombörjan -> eskalering --------


def test_output_contract_missing_keys_triggers_retry_then_escalate_on_second_miss():
    result_first = check_output_contract({}, required_context_refs=(), already_retried=False)
    assert result_first.verdict == "retry"
    result_second = check_output_contract({}, required_context_refs=(), already_retried=True)
    assert result_second.verdict == "escalate"


def test_output_contract_ok_when_declared_ref_present():
    output = _valid_output()
    result = check_output_contract(
        output, required_context_refs=("context_pack",), already_retried=False
    )
    assert result.verdict == "ok"


def test_run_playbook_step_retries_once_then_succeeds():
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    ledger = RunLedger(satisfied={"context_pack"})
    attempts = []

    def execute(rendered: str) -> dict:
        attempts.append(rendered)
        if len(attempts) == 1:
            return {}  # första försöket: saknar kontraktet
        return _valid_output()

    output = run_playbook_step(step, ledger, execute=execute)
    assert len(attempts) == 2, "steget skulle försökts en gång till efter en missad referens."
    assert output.get("escalated") is not True


def test_run_playbook_step_escalates_after_second_miss_instead_of_silently_continuing():
    step = PlaybookStep(
        skill="mk:offers", requires=("context_pack",), condition=None
    )
    ledger = RunLedger(satisfied={"context_pack"})

    def execute(rendered: str) -> dict:
        return {"sources_used": [], "context_refs": []}  # saknar deklarerad ref varje gång

    output = run_playbook_step(
        step, ledger, execute=execute, required_context_refs=("value_equation_scores",)
    )
    assert output["escalated"] is True
    assert "value_equation_scores" in output["escalation_reason"]


# -- Plan Verifiering, ordagrant: "sources_used[] faktiskt refererar paketet"


def test_output_contract_fails_when_context_pack_is_not_referenced_in_context_refs():
    output = {"sources_used": ["kb-artikel-1"], "context_refs": []}  # kontextpaketet ANVÄNDES inte
    result = check_output_contract(
        output, required_context_refs=("context_pack",), already_retried=True
    )
    assert result.verdict == "escalate"
    assert "context_pack" in result.missing_refs


def test_output_contract_passes_when_context_pack_is_referenced():
    output = {"sources_used": ["kb-artikel-1"], "context_refs": ["context_pack"]}
    result = check_output_contract(
        output, required_context_refs=("context_pack",), already_retried=False
    )
    assert result.verdict == "ok"


# -- Multi-steg: rätt ordning, villkorade steg, flera scenarier ------------


def _support_playbook() -> Playbook:
    return Playbook(
        name="support/v1-test",
        steps=(
            PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",)),
            PlaybookStep(skill="cs:customer-research", requires=("skill:cs:ticket-triage",)),
            PlaybookStep(skill="cs:draft-response", requires=("skill:cs:customer-research",)),
            PlaybookStep(
                skill="snajp:humanizer",
                requires=("skill:cs:draft-response",),
                condition="cancellation_risk",
            ),
            PlaybookStep(skill="snajp:humanizer-svenska", requires=("skill:cs:draft-response",)),
        ),
    )


def test_full_playbook_executes_every_declared_skill_in_order():
    """Scenario 1: inget eskaleringsvillkor — retention-steget hoppas över,
    resten körs i exakt deklarerad ordning."""
    playbook = _support_playbook()
    ledger = RunLedger(satisfied={"context_pack"})
    received = []

    def execute(step: PlaybookStep, rendered: str) -> dict:
        received.append((step.skill, len(rendered)))
        return _valid_output()

    run_playbook(
        playbook,
        ledger,
        execute=execute,
        should_run=lambda step, ledger: False,  # aldrig uppsägningsrisk i detta scenario
    )

    assert ledger.executed_order == [
        "cs:ticket-triage",
        "cs:customer-research",
        "cs:draft-response",
        "snajp:humanizer-svenska",
    ], "Ett villkorslöst steg saknades eller kördes i fel ordning."
    assert "snajp:humanizer" not in ledger.executed_order
    # Varje kört steg fick faktiskt en icke-trivial mängd text injicerad —
    # inte ett tomt anrop som bara låtsas ha läst skillen.
    assert all(length > 100 for _, length in received)


def test_full_playbook_runs_conditional_step_when_triggered():
    """Scenario 2: uppsägningsrisk -> retention-steget triggas OCKSÅ, fortfarande i ordning."""
    playbook = _support_playbook()
    ledger = RunLedger(satisfied={"context_pack"})

    def execute(step: PlaybookStep, rendered: str) -> dict:
        return _valid_output()

    run_playbook(
        playbook,
        ledger,
        execute=execute,
        should_run=lambda step, ledger: step.condition == "cancellation_risk",
    )

    assert ledger.executed_order == [
        "cs:ticket-triage",
        "cs:customer-research",
        "cs:draft-response",
        "snajp:humanizer",
        "snajp:humanizer-svenska",
    ]


def test_full_playbook_scenario_where_a_step_never_satisfies_its_contract():
    """Scenario 3: ett steg mitt i kedjan misslyckas upprepat med kontraktet
    -> eskaleras, men resten av kedjan fortsätter köra (agenten skickar
    fortfarande ett hållsvar, den fastnar inte)."""
    playbook = _support_playbook()
    ledger = RunLedger(satisfied={"context_pack"})

    def execute(step: PlaybookStep, rendered: str) -> dict:
        if step.skill == "cs:customer-research":
            return {"sources_used": [], "context_refs": []}  # saknar alltid kontraktet
        return _valid_output()

    run_playbook(
        playbook,
        ledger,
        execute=execute,
        required_context_refs_by_skill={"cs:customer-research": ("prior_tickets",)},
        should_run=lambda step, ledger: False,
    )

    assert ledger.executed_order == [
        "cs:ticket-triage",
        "cs:customer-research",
        "cs:draft-response",
        "snajp:humanizer-svenska",
    ], "Ett steg som eskalerar ska inte stoppa resten av kedjan."
    assert ledger.step_outputs["cs:customer-research"]["escalated"] is True
    assert ledger.step_outputs["cs:draft-response"].get("escalated") is not True
