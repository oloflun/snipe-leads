"""INV-SKILL-002 (requires[] obligatoriskt) och INV-SKILL-003 (skopa kräver rationale)."""

import pytest

from app.agentcore.packs import (
    MissingRequirementError,
    PlaybookStep,
    ScopeWithoutRationaleError,
)


def test_step_without_requires_raises():
    with pytest.raises(MissingRequirementError):
        PlaybookStep(skill="cs:ticket-triage", requires=())


def test_step_with_requires_is_fine():
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    assert step.skill == "cs:ticket-triage"


def test_scoped_step_without_rationale_raises():
    with pytest.raises(ScopeWithoutRationaleError):
        PlaybookStep(
            skill="mk:sales-enablement",
            requires=("context_pack",),
            scope=("references/objection-library.md",),
        )


def test_scoped_step_with_rationale_is_fine():
    step = PlaybookStep(
        skill="mk:sales-enablement",
        requires=("context_pack",),
        scope=("references/objection-library.md",),
        rationale="Kall e-post behöver invändningar, inte pitchdeck eller demoskript.",
    )
    rendered = step.render()
    assert "SKOPAD LADDNING" in rendered
    assert "objection" in rendered.lower() or "invänd" in rendered.lower()


def test_unscoped_step_renders_full_skill_md():
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    rendered = step.render()
    assert len(rendered) > 200
    assert "SKOPAD LADDNING" not in rendered


def test_step_construction_rejects_unprefixed_skill():
    from app.agentcore.registry import UnprefixedSkillNameError

    with pytest.raises(UnprefixedSkillNameError):
        PlaybookStep(skill="ticket-triage", requires=("context_pack",))


def test_thinking_defaults_to_none_meaning_inherit_global():
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    assert step.thinking is None


def test_thinking_override_accepts_enabled_or_disabled():
    enabled = PlaybookStep(skill="cs:ticket-triage", requires=("x",), thinking="enabled")
    disabled = PlaybookStep(skill="cs:ticket-triage", requires=("x",), thinking="disabled")
    assert enabled.thinking == "enabled"
    assert disabled.thinking == "disabled"


def test_thinking_override_rejects_invalid_value():
    with pytest.raises(ValueError):
        PlaybookStep(skill="cs:ticket-triage", requires=("x",), thinking="maybe")
