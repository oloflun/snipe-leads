from app.agentcore.registry import UnprefixedSkillNameError
from app.agentcore.packs import PlaybookStep
from app.leads.onboarding_playbook import ONBOARDING_V1, render_onboarding_instructions


def test_onboarding_playbook_declares_fas_a_skills_in_order():
    assert [s.skill for s in ONBOARDING_V1.steps] == [
        "mk:product-marketing",
        "mk:customer-research",
        "mk:churn-prevention",
    ]


def test_render_executes_all_three_steps_in_order_when_starting_fresh():
    instructions, ledger = render_onboarding_instructions()
    assert ledger.executed_order == [
        "mk:product-marketing",
        "mk:customer-research",
        "mk:churn-prevention",
    ]
    assert "Inget kontextdokument insamlat" in instructions


def test_render_shows_existing_context_when_resuming():
    instructions, ledger = render_onboarding_instructions(
        existing_product_marketing="# Livrustning\nRedan insamlat."
    )
    assert "Redan insamlat kontextdokument" in instructions
    assert "Livrustning" in instructions
    assert ledger.executed_order == [
        "mk:product-marketing",
        "mk:customer-research",
        "mk:churn-prevention",
    ]


def test_every_step_has_real_content_injected():
    instructions, _ = render_onboarding_instructions()
    assert "product marketing" in instructions.lower() or "produktmarknadsföring" in instructions.lower()
    assert "churn" in instructions.lower() or "retention" in instructions.lower()
