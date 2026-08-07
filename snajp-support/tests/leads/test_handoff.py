from app.leads.handoff import CALL_PREP_V1, render_call_prep_instructions, route_handoff


def test_call_prep_playbook_has_exactly_sa_call_prep():
    assert [s.skill for s in CALL_PREP_V1.steps] == ["sa:call-prep"]


def test_render_call_prep_states_agent_never_books_or_negotiates():
    instructions, ledger = render_call_prep_instructions()
    assert ledger.executed_order == ["sa:call-prep"]
    assert "du bokar inte själv" in instructions
    assert "du förhandlar inte pris" in instructions


def test_route_handoff_returns_a_record_not_a_booking():
    record = route_handoff(
        prospect_id="p-1",
        tenant_id="t-1",
        reason="positive_reply",
        tenant_primary_contact="anna@livrustning.se",
    )
    assert record.assigned_to == "anna@livrustning.se"
    assert record.speed_to_lead_target_minutes == 30
    # HandoffRecord har inget booking-fält att fylla i — strukturellt
    # omöjligt för den här funktionen att "boka" något.
    assert not hasattr(record, "meeting_time")
    assert not hasattr(record, "calendar_event_id")


def test_route_handoff_without_a_known_contact_leaves_assigned_to_none():
    record = route_handoff(
        prospect_id="p-2", tenant_id="t-1", reason="positive_reply", tenant_primary_contact=None
    )
    assert record.assigned_to is None
