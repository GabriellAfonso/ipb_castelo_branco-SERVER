import calendar
from datetime import date

from features.core.application.services.monthly_scheduler import (
    _next_month_from,
    _month_dates_for_weekday,
)


# --- _next_month_from ---


def test_standard_month_increments() -> None:
    assert _next_month_from(date(2026, 4, 15)) == (2026, 5)


def test_november_goes_to_december() -> None:
    assert _next_month_from(date(2026, 11, 1)) == (2026, 12)


def test_december_rolls_year() -> None:
    assert _next_month_from(date(2026, 12, 31)) == (2027, 1)


def test_december_day_irrelevant() -> None:
    assert _next_month_from(date(2025, 12, 1)) == (2026, 1)
    assert _next_month_from(date(2025, 12, 15)) == (2026, 1)


def test_january_to_february() -> None:
    assert _next_month_from(date(2026, 1, 1)) == (2026, 2)


# --- _month_dates_for_weekday ---


def test_returns_correct_sundays_may_2025() -> None:
    sundays = _month_dates_for_weekday(2025, 5, calendar.SUNDAY)
    assert [d.day for d in sundays] == [4, 11, 18, 25]


def test_returns_five_sundays_january_2023() -> None:
    sundays = _month_dates_for_weekday(2023, 1, calendar.SUNDAY)
    assert len(sundays) == 5


def test_all_dates_are_correct_weekday() -> None:
    for weekday_const, cal_val in [
        (calendar.SUNDAY, 6),
        (calendar.TUESDAY, 1),
        (calendar.THURSDAY, 3),
    ]:
        dates = _month_dates_for_weekday(2026, 3, weekday_const)
        assert all(d.weekday() == cal_val for d in dates), (
            f"Expected weekday {cal_val}, got {[d.weekday() for d in dates]}"
        )


def test_february_non_leap_stays_within_28() -> None:
    dates = _month_dates_for_weekday(2025, 2, calendar.SUNDAY)
    assert all(d.day <= 28 for d in dates)
    assert all(d.month == 2 for d in dates)


def test_february_leap_year_accepts_29() -> None:
    dates = _month_dates_for_weekday(2024, 2, calendar.THURSDAY)
    assert max(d.day for d in dates) <= 29
    assert all(d.month == 2 for d in dates)


def test_returns_list_of_date_objects() -> None:
    result = _month_dates_for_weekday(2026, 5, calendar.SUNDAY)
    assert isinstance(result, list)
    assert all(isinstance(d, date) for d in result)
