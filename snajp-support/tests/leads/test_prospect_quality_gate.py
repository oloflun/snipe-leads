import pytest

from app.leads.prospect_quality_gate import ProspectCandidate, ProspectQualityError, check_confidence_is_honest, check_contact_channel_is_lawful, check_not_duplicate, check_ready_for_outreach


def _candidate(**overrides) -> ProspectCandidate:
    defaults = dict(
        company_name="Acme AB",
        contact_email="info@acme.se",
        email_verified=True,
        source_count=1,
        confidence="medium",
        lawful_basis=None,
    )
    defaults.update(overrides)
    return ProspectCandidate(**defaults)


def test_duplicate_by_company_name_is_case_and_whitespace_insensitive():
    with pytest.raises(ProspectQualityError):
        check_not_duplicate(_candidate(company_name="  acme ab  "), {"Acme AB"})


def test_not_a_duplicate_passes():
    check_not_duplicate(_candidate(company_name="Other AB"), {"Acme AB"})


def test_high_confidence_requires_two_sources():
    with pytest.raises(ProspectQualityError):
        check_confidence_is_honest(_candidate(confidence="high", source_count=1))


def test_high_confidence_with_two_sources_passes():
    check_confidence_is_honest(_candidate(confidence="high", source_count=2))


def test_low_confidence_with_one_source_is_fine():
    check_confidence_is_honest(_candidate(confidence="low", source_count=1))


def test_personal_email_without_lawful_basis_blocked():
    with pytest.raises(ProspectQualityError):
        check_contact_channel_is_lawful(_candidate(contact_email="anna@gmail.com", lawful_basis=None))


def test_personal_email_with_lawful_basis_allowed():
    check_contact_channel_is_lawful(
        _candidate(contact_email="anna@gmail.com", lawful_basis="Opt-in via kontaktformulär 2026-01-01")
    )


def test_business_email_never_needs_lawful_basis_field():
    check_contact_channel_is_lawful(_candidate(contact_email="info@acme.se", lawful_basis=None))


def test_ready_for_outreach_rejects_missing_contact():
    with pytest.raises(ProspectQualityError):
        check_ready_for_outreach(_candidate(contact_email=None))


def test_ready_for_outreach_rejects_unverified_email():
    with pytest.raises(ProspectQualityError):
        check_ready_for_outreach(_candidate(email_verified=False))


def test_ready_for_outreach_passes_a_clean_candidate():
    check_ready_for_outreach(_candidate())
