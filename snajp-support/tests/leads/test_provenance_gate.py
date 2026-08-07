from datetime import datetime, timedelta

import pytest

from app.leads.provenance_gate import ProvenanceGateError, SourceRecord, check_provenance


def test_no_sources_at_all_raises():
    with pytest.raises(ProvenanceGateError):
        check_provenance([])


def test_linkedin_as_only_source_raises():
    with pytest.raises(ProvenanceGateError):
        check_provenance([SourceRecord("linkedin", datetime(2026, 1, 1))])


def test_linkedin_as_earliest_source_raises_even_if_other_sources_exist_later():
    sources = [
        SourceRecord("linkedin", datetime(2026, 1, 1)),
        SourceRecord("company_website", datetime(2026, 1, 5)),
    ]
    with pytest.raises(ProvenanceGateError):
        check_provenance(sources)


def test_linkedin_as_verification_after_another_source_is_allowed():
    sources = [
        SourceRecord("company_website", datetime(2026, 1, 1)),
        SourceRecord("linkedin", datetime(2026, 1, 5)),  # verifiering, inte upptäckt
    ]
    check_provenance(sources)  # kastar inte


def test_non_linkedin_first_source_is_fine():
    sources = [SourceRecord("public_news", datetime(2026, 1, 1) + timedelta(hours=1))]
    check_provenance(sources)
