"""Occurrence collapsing rules. No database — these are pure functions.

Weekday convention: 0 = Monday ... 6 = Sunday. Sunday is 6, not 0.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from features.songs.hymnal_history_dtos import (
    GROUP_BY_DAY,
    GROUP_BY_MONTH,
    GROUP_BY_SERVICE,
    GROUP_BY_WEEK,
)
from core.models import ChurchService
from core.domain.weekday import from_python_weekday
from features.songs.services.hymnal_history_occurrences import (
    bucket_label,
    collapse_events,
    group_events,
    hymn_sort_key,
    match_window,
)

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
LABELS = {1: ("50", "Grandioso És Tu"), 2: ("120", "Saudosa Lembrança")}

# Sunday 9 August 2026 — weekday() == 6
SUNDAY_EVENING = datetime(2026, 8, 9, 19, 30, tzinfo=SAO_PAULO)
SUNDAY_MORNING = datetime(2026, 8, 9, 10, 45, tzinfo=SAO_PAULO)
WEDNESDAY_AFTERNOON = datetime(2026, 8, 12, 15, 0, tzinfo=SAO_PAULO)


def _window(
    window_id: int = 1,
    name: str = "Culto de Domingo à Noite",
    weekday: int = 1,
    start: time = time(19, 0),
    end: time = time(21, 0),
    active: bool = True,
) -> ChurchService:
    return ChurchService(
        id=window_id, name=name, weekday=weekday, start_time=start, end_time=end, active=active
    )


EVENING = _window()
MORNING = _window(2, "Culto de Domingo pela Manhã", 1, time(10, 30), time(12, 0))


class TestSundayIsWeekdayOne:
    def test_the_convention_holds(self) -> None:
        """Python still says 6 for Sunday; the catalogue stores 1."""
        assert SUNDAY_EVENING.weekday() == 6
        assert from_python_weekday(SUNDAY_EVENING.weekday()) == 1
        assert from_python_weekday(WEDNESDAY_AFTERNOON.weekday()) == 4


class TestMatchWindow:
    def test_matches_the_containing_window(self) -> None:
        assert match_window(SUNDAY_EVENING, [EVENING, MORNING]) is EVENING

    def test_no_match_outside_every_window(self) -> None:
        assert match_window(WEDNESDAY_AFTERNOON, [EVENING, MORNING]) is None

    def test_no_match_with_no_windows(self) -> None:
        assert match_window(SUNDAY_EVENING, []) is None

    def test_start_time_is_inside(self) -> None:
        at_start = datetime(2026, 8, 9, 19, 0, tzinfo=SAO_PAULO)
        assert match_window(at_start, [EVENING]) is EVENING

    def test_end_time_is_inside_thanks_to_the_grace_period(self) -> None:
        """A service that runs a little long still owns the hymn (grace = 30 min)."""
        at_end = datetime(2026, 8, 9, 21, 0, tzinfo=SAO_PAULO)
        assert match_window(at_end, [EVENING]) is EVENING

    def test_within_the_grace_period_still_matches(self) -> None:
        overtime = datetime(2026, 8, 9, 21, 25, tzinfo=SAO_PAULO)
        assert match_window(overtime, [EVENING]) is EVENING

    def test_end_of_the_grace_period_is_outside(self) -> None:
        """Half-open at the far end, so the window cannot claim forever."""
        past_grace = datetime(2026, 8, 9, 21, 30, tzinfo=SAO_PAULO)
        assert match_window(past_grace, [EVENING]) is None

    def test_grace_of_zero_makes_end_time_exclusive(self) -> None:
        at_end = datetime(2026, 8, 9, 21, 0, tzinfo=SAO_PAULO)
        assert match_window(at_end, [EVENING], grace_minutes=0) is None

    def test_grace_never_extends_the_start(self) -> None:
        """Opening a hymn before the service is preparing, not singing along."""
        before = datetime(2026, 8, 9, 18, 59, tzinfo=SAO_PAULO)
        assert match_window(before, [EVENING]) is None

    def test_grace_crossing_midnight_does_not_wrap(self) -> None:
        late = _window(9, "Vigília", 1, time(22, 0), time(23, 50))
        inside = datetime(2026, 8, 10, 0, 10, tzinfo=SAO_PAULO)
        # 00:10 on the 10th is Monday, so it must not match a Sunday window...
        assert match_window(inside, [late]) is None
        # ...but 23:55 on the Sunday itself is inside the grace period.
        assert match_window(datetime(2026, 8, 9, 23, 55, tzinfo=SAO_PAULO), [late]) is late

    def test_wrong_weekday_does_not_match(self) -> None:
        monday_evening = datetime(2026, 8, 10, 19, 30, tzinfo=SAO_PAULO)
        assert match_window(monday_evening, [EVENING]) is None

    def test_overlapping_windows_earliest_start_wins(self) -> None:
        late = _window(3, "Late", 1, time(19, 15), time(21, 0))
        assert match_window(SUNDAY_EVENING, [late, EVENING]) is EVENING
        assert match_window(SUNDAY_EVENING, [EVENING, late]) is EVENING


class TestBucketLabel:
    def test_service_bucket(self) -> None:
        assert bucket_label(date(2026, 8, 9), 3, GROUP_BY_SERVICE) == "2026-08-09:3"

    def test_service_bucket_without_a_window(self) -> None:
        assert bucket_label(date(2026, 8, 9), None, GROUP_BY_SERVICE) == "2026-08-09:none"

    def test_day_bucket(self) -> None:
        assert bucket_label(date(2026, 8, 9), 3, GROUP_BY_DAY) == "2026-08-09"

    def test_week_bucket_is_iso(self) -> None:
        assert bucket_label(date(2026, 8, 9), 3, GROUP_BY_WEEK) == "2026-W32"

    def test_month_bucket(self) -> None:
        assert bucket_label(date(2026, 8, 9), 3, GROUP_BY_MONTH) == "2026-08"


class TestHymnSortKey:
    def test_numeric_prefix_drives_the_order(self) -> None:
        assert sorted(["110", "9", "12"], key=hymn_sort_key) == ["9", "12", "110"]

    def test_alphanumeric_suffix(self) -> None:
        assert hymn_sort_key("110-A") == (110, "110-A")

    def test_non_numeric_number_does_not_crash(self) -> None:
        assert hymn_sort_key("A") == (0, "A")


class TestGroupEvents:
    def test_three_devices_in_one_window_are_one_occurrence(self) -> None:
        events = [
            (1, SUNDAY_EVENING, "dev-a"),
            (1, SUNDAY_EVENING, "dev-b"),
            (1, SUNDAY_EVENING, "dev-c"),
        ]
        grouped = group_events(events, [EVENING])
        assert len(grouped) == 1
        assert grouped[(1, 1, date(2026, 8, 9))] == {"dev-a", "dev-b", "dev-c"}

    def test_same_device_twice_still_counts_once(self) -> None:
        events = [(1, SUNDAY_EVENING, "dev-a"), (1, SUNDAY_EVENING, "dev-a")]
        grouped = group_events(events, [EVENING])
        assert grouped[(1, 1, date(2026, 8, 9))] == {"dev-a"}

    def test_morning_and_evening_are_two_occurrences(self) -> None:
        events = [(1, SUNDAY_MORNING, "dev-a"), (1, SUNDAY_EVENING, "dev-a")]
        grouped = group_events(events, [EVENING, MORNING])
        assert len(grouped) == 2

    def test_outside_every_window_collapses_by_calendar_day(self) -> None:
        events = [
            (2, WEDNESDAY_AFTERNOON, "dev-a"),
            (2, datetime(2026, 8, 12, 16, 30, tzinfo=SAO_PAULO), "dev-b"),
        ]
        grouped = group_events(events, [EVENING])
        assert len(grouped) == 1
        assert grouped[(2, None, date(2026, 8, 12))] == {"dev-a", "dev-b"}

    def test_no_windows_configured_still_groups_by_day(self) -> None:
        events = [(1, SUNDAY_EVENING, "dev-a"), (1, SUNDAY_MORNING, "dev-b")]
        grouped = group_events(events, [])
        assert len(grouped) == 1

    def test_utc_timestamps_bucket_by_local_date(self) -> None:
        """22:30 UTC on the 10th is 19:30 local on the 9th — a Sunday service."""
        utc_moment = datetime(2026, 8, 9, 22, 30, tzinfo=ZoneInfo("UTC"))
        grouped = group_events([(1, utc_moment, "dev-a")], [EVENING])
        assert list(grouped.keys()) == [(1, 1, date(2026, 8, 9))]


class TestCollapseEvents:
    def test_reports_hymn_labels_and_device_count(self) -> None:
        events = [(1, SUNDAY_EVENING, "dev-a"), (1, SUNDAY_EVENING, "dev-b")]
        result = collapse_events(events, [EVENING], LABELS, GROUP_BY_SERVICE)
        assert len(result) == 1
        assert result[0].hymn_number == "50"
        assert result[0].hymn_title == "Grandioso És Tu"
        assert result[0].device_count == 2
        assert result[0].service_window_name == "Culto de Domingo à Noite"

    def test_no_window_reports_nulls(self) -> None:
        result = collapse_events([(2, WEDNESDAY_AFTERNOON, "dev-a")], [EVENING], LABELS)
        assert result[0].service_window_id is None
        assert result[0].service_window_name is None
        assert result[0].bucket == "2026-08-12:none"

    def test_grouping_never_changes_the_occurrence_count(self) -> None:
        events = [
            (1, SUNDAY_MORNING, "dev-a"),
            (1, SUNDAY_EVENING, "dev-b"),
            (2, WEDNESDAY_AFTERNOON, "dev-c"),
        ]
        counts = {
            group_by: len(collapse_events(events, [EVENING, MORNING], LABELS, group_by))
            for group_by in (GROUP_BY_SERVICE, GROUP_BY_DAY, GROUP_BY_WEEK, GROUP_BY_MONTH)
        }
        assert set(counts.values()) == {3}

    def test_ordering_is_date_then_window_start_then_hymn(self) -> None:
        events = [
            (2, WEDNESDAY_AFTERNOON, "dev-c"),
            (1, SUNDAY_EVENING, "dev-b"),
            (2, SUNDAY_MORNING, "dev-a"),
        ]
        result = collapse_events(events, [EVENING, MORNING], LABELS)
        assert [(o.hymn_number, o.occurred_on) for o in result] == [
            ("120", date(2026, 8, 9)),
            ("50", date(2026, 8, 9)),
            ("120", date(2026, 8, 12)),
        ]

    def test_inactive_windows_are_not_passed_in_and_events_fall_back(self) -> None:
        """The repository filters on active; with none supplied everything is day-collapsed."""
        result = collapse_events([(1, SUNDAY_EVENING, "dev-a")], [], LABELS)
        assert result[0].service_window_id is None

    def test_empty_input(self) -> None:
        assert collapse_events([], [EVENING], LABELS) == []
