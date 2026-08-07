"""Del J: tidsgrind. Gäller ENDAST outreach (leads) — support svarar direkt,
oavsett tid (A5, INV-TIME-001).

| Regel | Värde |
|---|---|
| Minsta väntan före svar | 60 minuter |
| Nytt/kallt utskick | 08:00-16:00 Europe/Stockholm |
| Svar i tråd där prospektet svarat | till 19:00 |
| Helger och svenska helgdagar | inga utskick |

Allt går genom send_queue.scheduled_at (migration 010). Schemaläggaren
(FastAPI-tjänsten, kommande task) kör dessa funktioner IGEN vid faktisk
utskickstid — en köad tid kan ha passerat fönstret sedan den köades.

Tolkning där planen inte stavar ut ett exakt klockslag: trådsvarsfönstret
(till 19:00) börjar liksom kallt-utskick vid 08:00 lokal tid, inte
klockan noll — ett automatiskt "trådsvar" klockan 03:00 vore lika
robotlikt som ett kallt utskick vid samma tid. Öppen fråga om detta visar
sig fel i praktiken; se plan "Öppna punkter"-anda (ta upp med användaren,
inte tyst).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

STOCKHOLM = ZoneInfo("Europe/Stockholm")

MIN_REPLY_DELAY = timedelta(minutes=60)
WINDOW_START_HOUR = 8
COLD_OUTREACH_END_HOUR = 16
THREAD_REPLY_END_HOUR = 19


class TimingGateError(RuntimeError):
    pass


def _easter_sunday(year: int) -> date:
    """Meeus/Jones/Butcher-algoritmen, gregoriansk kalender."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _midsummer_day(year: int) -> date:
    """Midsommardagen: lördagen mellan 20-26 juni."""
    for day in range(20, 27):
        candidate = date(year, 6, day)
        if candidate.weekday() == 5:  # lördag
            return candidate
    raise AssertionError("ingen lördag 20-26 juni — kalendermatematiken är trasig")


def swedish_no_send_dates(year: int) -> set[date]:
    """Röda dagar plus midsommarafton/julafton/nyårsafton — dagar då Snajp
    inte skickar outreach, inte en fullständig helgdagslista i juridisk
    mening."""
    easter = _easter_sunday(year)
    midsummer_day = _midsummer_day(year)
    return {
        date(year, 1, 1),                     # Nyårsdagen
        date(year, 1, 6),                      # Trettondedag jul
        easter - timedelta(days=2),            # Långfredagen
        easter,                                 # Påskdagen
        easter + timedelta(days=1),             # Annandag påsk
        date(year, 5, 1),                       # Första maj
        easter + timedelta(days=39),            # Kristi himmelsfärdsdag
        easter + timedelta(days=49),            # Pingstdagen
        date(year, 6, 6),                       # Nationaldagen
        midsummer_day - timedelta(days=1),      # Midsommarafton
        midsummer_day,                          # Midsommardagen
        date(year, 12, 24),                     # Julafton
        date(year, 12, 25),                     # Juldagen
        date(year, 12, 26),                     # Annandag jul
        date(year, 12, 31),                     # Nyårsafton
    }


def is_blocked_day(moment: datetime) -> bool:
    local = moment.astimezone(STOCKHOLM)
    if local.weekday() >= 5:  # lördag=5, söndag=6
        return True
    return local.date() in swedish_no_send_dates(local.year)


@dataclass(frozen=True)
class TimingCheckResult:
    allowed: bool
    reason: str | None = None


def check_cold_outreach_gate(moment: datetime) -> TimingCheckResult:
    """Nytt/kallt utskick: 08:00-16:00 Europe/Stockholm, ej helg/helgdag."""
    local = moment.astimezone(STOCKHOLM)
    if is_blocked_day(local):
        return TimingCheckResult(False, "helg eller svensk helgdag")
    if not (WINDOW_START_HOUR <= local.hour < COLD_OUTREACH_END_HOUR):
        return TimingCheckResult(
            False, f"utanför kallt-utskick-fönstret 08:00-16:00 (lokal tid {local:%H:%M})"
        )
    return TimingCheckResult(True)


def check_thread_reply_gate(
    moment: datetime, *, prospect_last_inbound_at: datetime
) -> TimingCheckResult:
    """Svar i tråd där prospektet svarat: fönster till 19:00, plus 60
    minuters minsta väntan sedan prospektets senaste meddelande."""
    local = moment.astimezone(STOCKHOLM)
    if is_blocked_day(local):
        return TimingCheckResult(False, "helg eller svensk helgdag")
    if moment - prospect_last_inbound_at < MIN_REPLY_DELAY:
        return TimingCheckResult(
            False, "under 60 minuters minsta väntan sedan prospektets senaste svar"
        )
    if not (WINDOW_START_HOUR <= local.hour < THREAD_REPLY_END_HOUR):
        return TimingCheckResult(
            False, f"utanför trådsvar-fönstret 08:00-19:00 (lokal tid {local:%H:%M})"
        )
    return TimingCheckResult(True)
