"""INV-SKILL-001: namnrymden är inte kosmetisk. Ett oprefixat namn kastar."""

import pytest

from app.agentcore.registry import (
    UnknownSkillError,
    UnprefixedSkillNameError,
    load_reference,
    load_skill_md,
    parse_skill_name,
    skill_exists,
)


def test_unprefixed_name_raises():
    with pytest.raises(UnprefixedSkillNameError):
        parse_skill_name("customer-research")


def test_unknown_namespace_raises():
    with pytest.raises(UnknownSkillError):
        parse_skill_name("xx:customer-research")


def test_unknown_skill_in_valid_namespace_raises():
    with pytest.raises(UnknownSkillError):
        parse_skill_name("mk:does-not-exist")


@pytest.mark.parametrize(
    "name",
    ["mk:cold-email", "mk:offers", "cs:ticket-triage", "sa:call-prep", "snajp:humanizer-svenska"],
)
def test_known_skills_resolve(name):
    ref = parse_skill_name(name)
    assert ref.qualified_name == name


def test_mk_and_cs_customer_research_are_different_skills():
    """Del D: samma namn, olika namnrymd, aldrig utbytbara."""
    mk = load_skill_md("mk:customer-research")
    cs = load_skill_md("cs:customer-research")
    assert mk != cs
    assert "kund" in mk.lower() or "customer" in mk.lower()


def test_skill_exists_does_not_raise():
    assert skill_exists("mk:cold-email") is True
    assert skill_exists("not-a-skill") is False
    assert skill_exists("zz:cold-email") is False


def test_load_reference_for_scoped_content():
    text = load_reference("mk:sales-enablement", "references/objection-library.md")
    assert len(text) > 100


def test_load_reference_missing_file_raises():
    from app.agentcore.registry import UnknownReferenceError

    with pytest.raises(UnknownReferenceError):
        load_reference("mk:sales-enablement", "references/does-not-exist.md")
