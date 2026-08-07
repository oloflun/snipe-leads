import pytest

from app.agentcore.registry import UnknownReferenceError, load_section


def test_extracts_exactly_the_named_section():
    section = load_section("mk:sales-enablement", "Objection Handling Docs")
    assert section.startswith("## Objection Handling Docs")
    assert "## ROI Calculators" not in section  # nästa sektion ska inte följa med
    assert "## One-Pagers" not in section  # föregående sektion ska inte finnas kvar


def test_unknown_section_raises():
    with pytest.raises(UnknownReferenceError):
        load_section("mk:sales-enablement", "Does Not Exist As A Heading")


def test_last_section_in_file_extracts_to_end_of_file():
    section = load_section("mk:sales-enablement", "Related Skills")
    assert section.startswith("## Related Skills")
    assert len(section) > 20
