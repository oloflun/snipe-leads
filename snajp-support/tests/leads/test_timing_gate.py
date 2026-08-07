"""Del J tidsgrind. Fryst klocka över exakt de tidpunkter Verifiering-
avsnittet i planen kräver: 07:59, 08:00, 16:01, 17:00, 19:01, lördag,
midsommarafton."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.leads.timing_gate import (
    STOCKHOLM,
    _midsummer_day,
    check_cold_outreach_gate,
    check_thread_reply_gate,
    is_blocked_day,
    swedish_no_send_dates,
)

# En vanlig onsdag utan helgdag i närheten.
WEEKDAY = date(2026, 8, 12)


def _at(hour: int, minute: int = 0, on: date = WEEKDAY) -> datetime:
    return datetime(on.year, on.month, on.day, hour, minute, tzinfo=STOCKHOLM)


# -- Kallt utskick: 08:00-16:00 ---------------------------------------------


def test_0759_blocked_before_window():
    result = check_cold_outreach_gate(_at(7, 59))
    assert result.allowed is False


def test_0800_allowed_at_window_open():
    result = check_cold_outreach_gate(_at(8, 0))
    assert result.allowed is True


def test_1600_blocked_at_cold_outreach_window_close():
    """16:00 exakt är UTANFÖR (halvöppet intervall [08:00, 16:00))."""
    result = check_cold_outreach_gate(_at(16, 0))
    assert result.allowed is False


def test_1601_blocked_after_window():
    result = check_cold_outreach_gate(_at(16, 1))
    assert result.allowed is False


def test_1559_allowed_just_before_close():
    result = check_cold_outreach_gate(_at(15, 59))
    assert result.allowed is True


# -- Trådsvar: till 19:00, plus 60 min minsta väntan ------------------------


def test_1700_allowed_within_thread_reply_window():
    prospect_replied_at = _at(15, 0)
    result = check_thread_reply_gate(_at(17, 0), prospect_last_inbound_at=prospect_replied_at)
    assert result.allowed is True


def test_1901_blocked_after_thread_reply_window():
    prospect_replied_at = _at(15, 0)
    result = check_thread_reply_gate(_at(19, 1), prospect_last_inbound_at=prospect_replied_at)
    assert result.allowed is False


def test_1900_blocked_at_thread_reply_window_close():
    prospect_replied_at = _at(15, 0)
    result = check_thread_reply_gate(_at(19, 0), prospect_last_inbound_at=prospect_replied_at)
    assert result.allowed is False


def test_thread_reply_blocked_under_60_minutes_since_prospect_message():
    prospect_replied_at = _at(10, 30)
    result = check_thread_reply_gate(_at(10, 45), prospect_last_inbound_at=prospect_replied_at)
    assert result.allowed is False
    assert "60 minuter" in result.reason


def test_thread_reply_allowed_at_exactly_60_minutes():
    prospect_replied_at = _at(10, 0)
    result = check_thread_reply_gate(_at(11, 0), prospect_last_inbound_at=prospect_replied_at)
    assert result.allowed is True


# -- Helg och helgdag --------------------------------------------------------


def test_saturday_blocks_cold_outreach():
    saturday = date(2026, 8, 15)  # onsdagen 2026-08-12 + 3 dagar
    assert saturday.weekday() == 5
    result = check_cold_outreach_gate(_at(10, 0, on=saturday))
    assert result.allowed is False
    assert "helg" in result.reason


def test_midsummer_eve_blocks_cold_outreach():
    midsummer_eve = _midsummer_day(2026) - timedelta(days=1)
    result = check_cold_outreach_gate(_at(10, 0, on=midsummer_eve))
    assert result.allowed is False
    assert "helgdag" in result.reason


def test_midsummer_eve_blocks_thread_reply_too():
    midsummer_eve = _midsummer_day(2026) - timedelta(days=1)
    prospect_replied_at = datetime(
        midsummer_eve.year, midsummer_eve.month, midsummer_eve.day, 9, 0, tzinfo=STOCKHOLM
    )
    result = check_thread_reply_gate(
        _at(12, 0, on=midsummer_eve), prospect_last_inbound_at=prospect_replied_at
    )
    assert result.allowed is False


def test_is_blocked_day_matches_check_gate_for_holidays():
    for holiday in sorted(swedish_no_send_dates(2026)):
        moment = datetime(holiday.year, holiday.month, holiday.day, 12, 0, tzinfo=STOCKHOLM)
        assert is_blocked_day(moment) is True
        assert check_cold_outreach_gate(moment).allowed is False


def test_utc_moment_is_converted_to_stockholm_before_checking():
    """Ett moment i UTC ska tolkas i Stockholm-tid, inte råka passera för att
    UTC-klockslaget råkar ligga inom fönstret."""
    # 06:00 UTC = 08:00 Stockholm (sommartid, CEST) i augusti.
    utc_moment = datetime(2026, 8, 12, 6, 0, tzinfo=ZoneInfo("UTC"))
    assert check_cold_outreach_gate(utc_moment).allowed is True
