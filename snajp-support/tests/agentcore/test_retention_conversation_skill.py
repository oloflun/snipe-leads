"""Strukturell kontroll av snajp:retention-conversation (plan A2). Fullt
beteendetest (att agenten faktiskt FÖLJER de fyra reglerna i ett riktigt
samtal) hör till verifieringssviten (task 15) när support-agenten är
ombyggd på cs:-playbooken (task 7) och kan köras end-to-end."""

from app.agentcore.registry import load_reference, load_skill_md

SKILL = load_skill_md("snajp:retention-conversation")
OBJECTIONS = load_reference(
    "snajp:retention-conversation", "references/support-objection-library.md"
)

FOUR_RULES = [
    "Erbjud aldrig något som inte står i kundens retentionsplaybook",
    "Ifrågasätt aldrig kundens beskrivning",
    "Ett ultimatum går alltid till människa",
    "Lova aldrig en tidpunkt kunden inte har auktoriserat",
]

OBJECTION_CATEGORIES = [
    "Brutet löfte",
    "Upprepat fel",
    "Tvivel på värdet",
    "Pris mot värde",
    "Ansträngning",
    "Ultimatum",
]


def test_skill_states_all_four_hard_rules():
    for rule in FOUR_RULES:
        assert rule in SKILL, f"Regel saknas i SKILL.md: {rule}"


def test_skill_is_distinct_from_churn_prevention_and_sales_objections():
    churn_prevention = load_skill_md("mk:churn-prevention")
    sales_objections = load_reference("mk:sales-enablement", "references/objection-library.md")
    assert SKILL != churn_prevention
    assert OBJECTIONS != sales_objections


def test_objection_library_covers_all_six_categories():
    for category in OBJECTION_CATEGORIES:
        assert category in OBJECTIONS, f"Kategori saknas i objektionsbiblioteket: {category}"


def test_ultimatum_category_states_it_always_escalates():
    ultimatum_section = OBJECTIONS.split("## 6. Ultimatum")[1]
    assert "escalate_to_human" in ultimatum_section
    assert "aldrig" in ultimatum_section.lower()
