"""Reporting use cases: occurrences by period and the hymn ranking."""

from datetime import date, datetime, time, timedelta

from django.utils import timezone

from core.domain.exceptions import ReportRangeError
from features.songs.hymnal_history_dtos import (
    OccurrenceDTO,
    ReportRangeDTO,
    TopHymnDTO,
)
from features.songs.repositories.interfaces import HymnalHistoryRepository
from features.songs.services.hymnal_history_occurrences import (
    collapse_events,
    group_events,
    hymn_sort_key,
)

# Keeps "fetch the range into memory" an honest promise (research R-04).
MAX_RANGE_DAYS = 366
DEFAULT_RANGE_DAYS = 30


class HymnalHistoryReportService:
    """Derives occurrences from stored view events at read time."""

    def __init__(self, repository: HymnalHistoryRepository) -> None:
        self._repository = repository

    def list_occurrences(self, report_range: ReportRangeDTO) -> list[OccurrenceDTO]:
        """Return the occurrences inside an inclusive local-date range.

        >>> service.list_occurrences(ReportRangeDTO(from_date=d1, to_date=d2))
        [OccurrenceDTO(hymn_number='50', ...)]
        """
        self._validate_range(report_range.from_date, report_range.to_date)
        start, end = self._to_aware_interval(report_range.from_date, report_range.to_date)

        events = self._repository.list_events_in_range(start, end)
        windows = self._repository.list_active_service_windows()
        labels = self._repository.get_hymn_labels({hymn_id for hymn_id, _, _ in events})
        grace = self._repository.get_settings().window_grace_minutes

        return collapse_events(events, windows, labels, report_range.group_by, grace)

    def top_hymns(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[TopHymnDTO]:
        """Rank hymns by occurrence count, descending.

        Counts occurrences, not raw events: five devices contributing to one
        occurrence count as one. Hymns with no occurrences are omitted — the client
        fills the gaps.

        The 366-day cap does not apply: the result is one row per hymn, so it is
        bounded by the size of the hymnal however much history exists.

        >>> service.top_hymns()
        [TopHymnDTO(hymn_number='50', hymn_title='Grandioso És Tu', occurrence_count=42)]
        """
        if from_date is not None and to_date is not None:
            self._validate_range(from_date, to_date, enforce_max_span=False)

        start = self._start_of_day(from_date) if from_date else None
        end = self._start_of_day(to_date + timedelta(days=1)) if to_date else None

        events = self._repository.list_events_in_range(start, end)
        windows = self._repository.list_active_service_windows()
        labels = self._repository.get_hymn_labels({hymn_id for hymn_id, _, _ in events})
        grace = self._repository.get_settings().window_grace_minutes

        counts: dict[int, int] = {}
        for hymn_id, _, _ in group_events(events, windows, grace):
            counts[hymn_id] = counts.get(hymn_id, 0) + 1

        ranked = [
            TopHymnDTO(
                hymn_number=labels.get(hymn_id, ("", ""))[0],
                hymn_title=labels.get(hymn_id, ("", ""))[1],
                occurrence_count=count,
            )
            for hymn_id, count in counts.items()
        ]
        return sorted(ranked, key=lambda h: (-h.occurrence_count, hymn_sort_key(h.hymn_number)))

    def _validate_range(
        self,
        from_date: date,
        to_date: date,
        enforce_max_span: bool = True,
    ) -> None:
        if from_date > to_date:
            raise ReportRangeError(from_date, to_date, "'from' must not be after 'to'")
        span = (to_date - from_date).days + 1
        if enforce_max_span and span > MAX_RANGE_DAYS:
            raise ReportRangeError(
                from_date,
                to_date,
                f"span of {span} days exceeds the maximum of {MAX_RANGE_DAYS}",
            )

    def _to_aware_interval(self, from_date: date, to_date: date) -> tuple[datetime, datetime]:
        """Convert inclusive local dates to a half-open aware interval.

        The half-open upper bound is what makes the last day's evening service appear.
        """
        return self._start_of_day(from_date), self._start_of_day(to_date + timedelta(days=1))

    def _start_of_day(self, day: date) -> datetime:
        naive = datetime.combine(day, time.min)
        return timezone.make_aware(naive, timezone.get_current_timezone())
