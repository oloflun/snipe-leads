from app.leads.research_playbook import RESEARCH_V1, render_research_instructions


def test_research_playbook_declares_fas_b_skills_in_a1_order():
    """A1: competitor-profiling FÖRE competitors, aldrig tvärtom."""
    skills = [s.skill for s in RESEARCH_V1.steps]
    assert skills == [
        "mk:customer-research",
        "mk:prospecting",
        "sa:account-research",
        "mk:competitor-profiling",
        "mk:competitors",
        "mk:sales-enablement",
        "mk:offers",
        "mk:ab-testing",
    ]
    assert skills.index("mk:competitor-profiling") < skills.index("mk:competitors")


def test_sales_enablement_step_is_scoped_with_rationale():
    step = next(s for s in RESEARCH_V1.steps if s.skill == "mk:sales-enablement")
    assert step.scope == ("§ Objection Handling Docs", "references/objection-library.md")
    assert step.rationale


def test_render_executes_every_step_in_order():
    instructions, ledger = render_research_instructions(
        tenant_name="Livrustning", context_pack="### Kontextpaket\nLivrustning säljer kurser."
    )
    assert ledger.executed_order == [
        "mk:customer-research",
        "mk:prospecting",
        "sa:account-research",
        "mk:competitor-profiling",
        "mk:competitors",
        "mk:sales-enablement",
        "mk:offers",
        "mk:ab-testing",
    ]
    assert "Livrustning säljer kurser" in instructions


def test_scoped_sales_enablement_content_excludes_demo_scripts_and_pitch_decks():
    """Del I:s poäng: en modell som fått demoskript i samma andetag börjar
    föreslå dem i ett kallt mejl. Den skopade laddningen ska INTE innehålla
    ROI-kalkylatorer eller demoskript-sektionerna."""
    instructions, _ = render_research_instructions(tenant_name="X", context_pack="ctx")
    scoped_block = instructions.split("### Skill: mk:sales-enablement")[1].split("### Skill:")[0]
    assert "Objection Handling" in scoped_block
    assert "Demo Scripts" not in scoped_block
    assert "ROI Calculators" not in scoped_block


def test_offers_step_pulls_in_all_seven_references_unscoped():
    instructions, _ = render_research_instructions(tenant_name="X", context_pack="ctx")
    offers_block = instructions.split("### Skill: mk:offers")[1].split("### Skill:")[0]
    for reference_file in (
        "value-equation.md",
        "offer-anatomy.md",
        "guarantee-design.md",
        "bonus-stacking.md",
        "scarcity-urgency.md",
        "offer-formats.md",
        "examples.md",
    ):
        assert reference_file in offers_block, f"{reference_file} saknas i mk:offers-blocket"
