"""Ranking rules, driven through FakeHymnalHistoryRepository — no database."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from core.domain.exceptions import ReportRangeError
from features.songs.hymnal_history_dtos import ReportRangeDTO
from core.models import ChurchService
from features.songs.models.hymnal_history import HymnalViewEvent
from features.songs.services.hymnal_history_report_service import HymnalHistoryReportService
from features.songs.tests.fakes import FakeHymnalHistoryRepository

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
LABELS = {1: ("50", "Grandioso És Tu"), 2: ("120", "Saudosa Lembrança"), 3: ("9", "Nono")}

SUNDAY_EVENING = datetime(2026, 8, 9, 19, 30, tzinfo=SAO_PAULO)
NEXT_SUNDAY_EVENING = datetime(2026, 8, 16, 19, 30, tzinfo=SAO_PAULO)

EVENING = ChurchService(
    id=1,
    name="Culto de Domingo à Noite",
    weekday=6,
    start_time=time(19, 0),
    end_time=time(21, 0),
    active=True,
)


def _event(hymn_id: int, moment: datetime, device_id: str) -> HymnalViewEvent:
    return HymnalViewEvent(
        client_event_id="00000000-0000-4000-8000-000000000000",
        hymn_id=hymn_id,
        device_id=device_id,
        viewed_at=moment,
        duration_seconds=40,
    )


def _service(events: list[HymnalViewEvent]) -> HymnalHistoryReportService:
    repo = FakeHymnalHistoryRepository(stored_events=events, windows=[EVENING], hymn_labels=LABELS)
    return HymnalHistoryReportService(repo)


class TestTopHymns:
    def test_five_devices_in_one_service_count_as_one(self) -> None:
        events = [_event(1, SUNDAY_EVENING, f"dev-{i}") for i in range(5)]
        result = _service(events).top_hymns()
        assert len(result) == 1
        assert result[0].occurrence_count == 1

    def test_two_services_count_as_two(self) -> None:
        events = [_event(1, SUNDAY_EVENING, "dev-a"), _event(1, NEXT_SUNDAY_EVENING, "dev-a")]
        assert _service(events).top_hymns()[0].occurrence_count == 2

    def test_hymns_without_occurrences_are_absent(self) -> None:
        result = _service([_event(1, SUNDAY_EVENING, "dev-a")]).top_hymns()
        assert [h.hymn_number for h in result] == ["50"]

    def test_ordered_by_count_descending(self) -> None:
        events = [
            _event(1, SUNDAY_EVENING, "dev-a"),
            _event(1, NEXT_SUNDAY_EVENING, "dev-a"),
            _event(2, SUNDAY_EVENING, "dev-a"),
        ]
        result = _service(events).top_hymns()
        assert [(h.hymn_number, h.occurrence_count) for h in result] == [("50", 2), ("120", 1)]

    def test_ties_break_on_hymn_number_numerically(self) -> None:
        events = [
            _event(1, SUNDAY_EVENING, "dev-a"),
            _event(2, SUNDAY_EVENING, "dev-a"),
            _event(3, SUNDAY_EVENING, "dev-a"),
        ]
        result = _service(events).top_hymns()
        assert [h.hymn_number for h in result] == ["9", "50", "120"]

    def test_range_filters_the_count(self) -> None:
        events = [_event(1, SUNDAY_EVENING, "dev-a"), _event(1, NEXT_SUNDAY_EVENING, "dev-a")]
        result = _service(events).top_hymns(date(2026, 8, 9), date(2026, 8, 9))
        assert result[0].occurrence_count == 1

    def test_no_range_covers_all_time(self) -> None:
        events = [_event(1, SUNDAY_EVENING, "dev-a"), _event(1, NEXT_SUNDAY_EVENING, "dev-a")]
        assert _service(events).top_hymns()[0].occurrence_count == 2

    def test_empty_history(self) -> None:
        assert _service([]).top_hymns() == []

    def test_span_over_366_days_is_allowed_for_the_ranking(self) -> None:
        """Bounded by hymnal size, not by history length."""
        result = _service([]).top_hymns(date(2020, 1, 1), date(2026, 1, 1))
        assert result == []

    def test_inverted_range_is_rejected(self) -> None:
        with pytest.raises(ReportRangeError):
            _service([]).top_hymns(date(2026, 8, 10), date(2026, 8, 9))


class TestListOccurrencesRangeValidation:
    def test_inverted_range_is_rejected(self) -> None:
        with pytest.raises(ReportRangeError) as exc:
            _service([]).list_occurrences(
                ReportRangeDTO(from_date=date(2026, 8, 10), to_date=date(2026, 8, 9))
            )
        assert "must not be after" in str(exc.value)

    def test_span_over_366_days_is_rejected(self) -> None:
        with pytest.raises(ReportRangeError) as exc:
            _service([]).list_occurrences(
                ReportRangeDTO(from_date=date(2025, 1, 1), to_date=date(2026, 8, 9))
            )
        assert "366" in str(exc.value)

    def test_exactly_366_days_is_allowed(self) -> None:
        result = _service([]).list_occurrences(
            ReportRangeDTO(from_date=date(2026, 1, 1), to_date=date(2027, 1, 1))
        )
        assert result == []

    def test_last_day_evening_is_included(self) -> None:
        """The half-open upper bound is what makes this work."""
        events = [_event(1, SUNDAY_EVENING, "dev-a")]
        result = _service(events).list_occurrences(
            ReportRangeDTO(from_date=date(2026, 8, 9), to_date=date(2026, 8, 9))
        )
        assert len(result) == 1
