import pytest

from app.leads.follow_up import FollowUpSequenceError, build_follow_up_sequence, weakest_lever


LIVRUSTNING_SCORES = {
    # Från plan Del H-exemplet: tidsfördröjning svagast, drömutfall starkast.
    "dream_outcome": 8,
    "perceived_likelihood": 5,
    "time_delay": 2,
    "effort_sacrifice": 4,
}


def test_weakest_lever_is_attacked_first():
    sequence = build_follow_up_sequence(LIVRUSTNING_SCORES)
    non_breakup = [s for s in sequence if not s.is_breakup]
    assert non_breakup[0].lever == "time_delay"
    assert non_breakup[-1].lever == "dream_outcome"


def test_sequence_ends_with_a_breakup_step():
    sequence = build_follow_up_sequence(LIVRUSTNING_SCORES)
    assert sequence[-1].is_breakup is True
    assert sequence[-1].lever is None


def test_sequence_has_one_step_per_lever_plus_breakup():
    sequence = build_follow_up_sequence(LIVRUSTNING_SCORES)
    assert len(sequence) == 5  # 4 spakar + breakup


def test_missing_lever_score_raises():
    with pytest.raises(FollowUpSequenceError):
        build_follow_up_sequence({"dream_outcome": 5})


def test_weakest_lever_helper_matches_sequence_order():
    assert weakest_lever(LIVRUSTNING_SCORES) == "time_delay"


def test_order_is_not_position_based_but_score_based():
    """Byt vilken spak som är svagast — sekvensen ska följa med, inte en
    fast tabellordning (det är precis skillnaden Del H beskriver)."""
    different_scores = {
        "dream_outcome": 2,  # nu svagast
        "perceived_likelihood": 8,
        "time_delay": 7,
        "effort_sacrifice": 6,
    }
    sequence = build_follow_up_sequence(different_scores)
    assert sequence[0].lever == "dream_outcome"
