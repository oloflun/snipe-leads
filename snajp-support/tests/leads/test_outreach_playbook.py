from app.leads.outreach_playbook import OUTREACH_V1, finalize_outreach_body, render_outreach_instructions


def test_outreach_playbook_order():
    assert [s.skill for s in OUTREACH_V1.steps] == [
        "sa:draft-outreach",
        "mk:cold-email",
        "mk:cold-email",
        "snajp:humanizer-svenska",
    ]


def test_render_executes_all_four_steps_in_order():
    instructions, ledger = render_outreach_instructions(
        tenant_name="Livrustning",
        company_name="Exempelbolaget AB",
        offer_summary="60 000 utbildade, 780 omdömen på Reco.se",
        context_pack="### Kontextpaket\n...",
    )
    assert ledger.executed_order == [
        "sa:draft-outreach",
        "mk:cold-email",
        "mk:cold-email",
        "snajp:humanizer-svenska",
    ]


def test_linkedin_output_is_explicitly_disabled_in_header():
    """G4: sa:draft-outreach producerar LinkedIn-kopia som standard — vår
    egen header måste uttryckligen stänga av det."""
    instructions, _ = render_outreach_instructions(
        tenant_name="X", company_name="Y", offer_summary="Z", context_pack=""
    )
    header = instructions.split("---")[0]
    assert "ALDRIG LinkedIn" in header


def test_plain_text_rule_is_stated_and_the_underlying_skill_confirms_it():
    instructions, _ = render_outreach_instructions(
        tenant_name="X", company_name="Y", offer_summary="Z", context_pack=""
    )
    assert "aldrig markdown" in instructions
    assert "No markdown formatting" in instructions  # sa:draft-outreach:s egen rad 291


def test_finalize_outreach_body_strips_markdown_the_humanizer_might_reintroduce():
    draft = "Hej!\n\n**Vi hjälper er** att spara tid.\n\n- Snabbare\n- Enklare"
    finalized = finalize_outreach_body(draft)
    assert "**" not in finalized
    assert finalized.startswith("Hej!")


def test_cold_email_scoped_step_only_pulls_personalization_reference():
    instructions, _ = render_outreach_instructions(
        tenant_name="X", company_name="Y", offer_summary="Z", context_pack=""
    )
    blocks = instructions.split("### Skill: mk:cold-email")
    scoped_block = blocks[1]
    assert "SKOPAD LADDNING" in scoped_block
    assert "personalization.md" in scoped_block
