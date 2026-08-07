from datetime import datetime

from app.leads.send_decision import decide_send_action
from app.leads.timing_gate import STOCKHOLM

WEEKDAY_MORNING = datetime(2026, 8, 12, 9, 0, tzinfo=STOCKHOLM)  # onsdag, inom fönstret
WEEKDAY_NIGHT = datetime(2026, 8, 12, 22, 0, tzinfo=STOCKHOLM)  # onsdag, utanför fönstret


def _thread(**overrides):
    base = {"language_state": "sv", "last_inbound_at": None}
    base.update(overrides)
    return base


def _message(**overrides):
    base = {"humanizer_variant": "snajp:humanizer-svenska"}
    base.update(overrides)
    return base


def test_sends_when_within_cold_outreach_window_and_gates_match():
    decision = decide_send_action(now=WEEKDAY_MORNING, thread=_thread(), message=_message())
    assert decision.action == "send"


def test_requeues_when_scheduled_time_has_drifted_outside_the_window():
    """Kärnan i Del J: en köad tid kan ha passerat fönstret sedan den köades."""
    decision = decide_send_action(now=WEEKDAY_NIGHT, thread=_thread(), message=_message())
    assert decision.action == "requeue"


def test_uses_thread_reply_window_when_prospect_has_replied():
    thread = _thread(last_inbound_at=datetime(2026, 8, 12, 17, 30, tzinfo=STOCKHOLM))
    decision = decide_send_action(
        now=datetime(2026, 8, 12, 18, 30, tzinfo=STOCKHOLM), thread=thread, message=_message()
    )
    assert decision.action == "send"  # inom 19:00-fönstret, >60 min sedan svaret


def test_blocks_on_language_variant_mismatch_instead_of_requeuing_forever():
    thread = _thread(language_state="en_confirmed")
    message = _message(humanizer_variant="snajp:humanizer-svenska")  # fel variant för en_confirmed
    decision = decide_send_action(now=WEEKDAY_MORNING, thread=thread, message=message)
    assert decision.action == "block"


def test_blocks_when_thread_or_message_missing():
    assert decide_send_action(now=WEEKDAY_MORNING, thread=None, message=_message()).action == "block"
    assert decide_send_action(now=WEEKDAY_MORNING, thread=_thread(), message=None).action == "block"


def test_requeues_on_a_swedish_holiday_regardless_of_hour():
    from datetime import timedelta

    from app.leads.timing_gate import _midsummer_day

    midsummer_eve = _midsummer_day(2026) - timedelta(days=1)
    now = datetime(midsummer_eve.year, midsummer_eve.month, midsummer_eve.day, 10, 0, tzinfo=STOCKHOLM)
    decision = decide_send_action(now=now, thread=_thread(), message=_message())
    assert decision.action == "requeue"
