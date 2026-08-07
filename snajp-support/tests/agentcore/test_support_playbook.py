"""support/v1:s deklarerade struktur (Del E). Att stegen FAKTISKT körs, i
ordning, med ett LLM-anrop var, bevisas i tests/agent/test_support_agent_wiring.py."""

from app.agent.support_playbook import SUPPORT_V1

FULL_ORDER_WITH_RETENTION = [
    "cs:ticket-triage",
    "cs:customer-research",
    "cs:draft-response",
    "cs:customer-escalation",
    "cs:kb-article",
    "snajp:retention-conversation",
    "snajp:humanizer-svenska",
]


def test_playbook_declares_seven_steps_in_del_e_order():
    assert [s.skill for s in SUPPORT_V1.steps] == FULL_ORDER_WITH_RETENTION


def test_only_retention_is_conditional():
    conditional = [s.skill for s in SUPPORT_V1.steps if s.condition]
    assert conditional == ["snajp:retention-conversation"]


def test_every_step_declares_requires_inv_skill_002():
    for step in SUPPORT_V1.steps:
        assert step.requires, f"{step.skill} saknar requires[]"


def test_humanizer_is_the_last_step_inv_lang_002():
    assert SUPPORT_V1.steps[-1].skill == "snajp:humanizer-svenska"


def test_each_step_renders_real_vendored_content():
    for step in SUPPORT_V1.steps:
        rendered = step.render()
        assert len(rendered) > 200, f"{step.skill} renderade misstänkt lite text"


def test_only_customer_escalation_overrides_thinking_to_enabled():
    """Beslut 2026-08-07: thinking AV överallt utom eskaleringsbedömningen."""
    overrides = {s.skill: s.thinking for s in SUPPORT_V1.steps if s.thinking is not None}
    assert overrides == {"cs:customer-escalation": "enabled"}
