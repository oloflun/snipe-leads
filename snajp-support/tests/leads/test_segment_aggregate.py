"""G11 Verifiering-krav: 'test att aggregatet döljs vid färre än tre kunder,
och att ingen prospekt- eller mejltext läcker genom vyn.'"""

import dataclasses

from app.leads.segment_aggregate import (
    MIN_TENANTS_PER_SEGMENT,
    AbResultRow,
    SegmentAggregateRow,
    compute_segment_aggregate,
)


def _row(tenant_id, segment="utbildning", lever="time_delay", sent=10, replies=2, positive=1):
    return AbResultRow(
        tenant_id=tenant_id, segment=segment, lever=lever, sent=sent, replies=replies, positive=positive
    )


def test_segment_with_fewer_than_three_tenants_is_completely_hidden():
    rows = [_row("t1"), _row("t2")]  # bara två tenants
    result = compute_segment_aggregate(rows)
    assert result == []


def test_segment_with_exactly_three_tenants_becomes_visible():
    rows = [_row("t1"), _row("t2"), _row("t3")]
    result = compute_segment_aggregate(rows)
    assert len(result) == 1
    assert result[0].tenant_count == 3


def test_segment_with_more_than_three_tenants_is_visible_and_summed():
    rows = [_row("t1", sent=10, replies=2, positive=1), _row("t2", sent=20, replies=4, positive=2), _row("t3", sent=5, replies=1, positive=0), _row("t4", sent=15, replies=3, positive=1)]
    result = compute_segment_aggregate(rows)
    assert result[0].tenant_count == 4
    assert result[0].sent == 50
    assert result[0].replies == 10
    assert result[0].positive == 4


def test_multiple_rows_from_the_same_tenant_still_count_as_one_tenant():
    """Om en tenant råkar bidra med flera rader till samma (segment, lever)
    ska det INTE räknas som flera olika kunder — annars går det att lura
    tröskeln genom att duplicera en enda kunds data."""
    rows = [_row("t1"), _row("t1"), _row("t2")]
    result = compute_segment_aggregate(rows)
    assert result == []  # fortfarande bara 2 DISTINKTA tenants


def test_different_segments_are_independent():
    rows = [
        _row("t1", segment="utbildning"),
        _row("t2", segment="utbildning"),
        _row("t3", segment="utbildning"),
        _row("t4", segment="e-handel"),  # bara en tenant i det här segmentet
    ]
    result = compute_segment_aggregate(rows)
    segments = {r.segment for r in result}
    assert segments == {"utbildning"}


def test_different_levers_within_the_same_segment_are_independent():
    rows = [
        _row("t1", lever="time_delay"),
        _row("t2", lever="time_delay"),
        _row("t3", lever="time_delay"),
        _row("t1", lever="effort_sacrifice"),  # bara en tenant för den här spaken
    ]
    result = compute_segment_aggregate(rows)
    assert len(result) == 1
    assert result[0].lever == "time_delay"


def test_output_row_has_no_field_that_could_identify_a_tenant_prospect_or_message():
    """Strukturell kontroll: SegmentAggregateRow kan inte ens INNEHÅLLA
    tenant_id, prospekt- eller mejlfält — inte bara 'råkar inte fyllas i'."""
    field_names = {f.name for f in dataclasses.fields(SegmentAggregateRow)}
    forbidden = {"tenant_id", "prospect_id", "company_name", "contact_email", "body", "message"}
    assert field_names.isdisjoint(forbidden)
    assert field_names == {"segment", "lever", "tenant_count", "sent", "replies", "positive"}


def test_min_tenants_constant_is_three_matching_the_plan():
    assert MIN_TENANTS_PER_SEGMENT == 3
