"""Pure rules turning raw view events into occurrences.

An **occurrence** is a hymn sung once by the congregation, not once per person:
every view of the same hymn inside the same service window collapses into one.
Views matching no active window collapse by hymn plus calendar day instead.

Derived at read time and never stored, so editing a service window changes future
reports without rewriting a single event.

No ORM, no HTTP, no clock — everything is passed in.
"""

from datetime import date, datetime, timedelta
from typing import Callable, Iterable

from django.utils import timezone

from features.songs.hymnal_history_dtos import (
    GROUP_BY_DAY,
    GROUP_BY_MONTH,
    GROUP_BY_SERVICE,
    GROUP_BY_WEEK,
    OccurrenceDTO,
)
from core.domain.weekday import from_python_weekday
from core.models import ChurchService
from features.songs.hymn_numbering import hymn_sort_key

# (hymn_id, service_window_id or None, local date)
OccurrenceKey = tuple[int, int | None, date]

NO_WINDOW_BUCKET_SUFFIX = "none"

# Fallback when no settings row is supplied; the stored value is what actually applies.
DEFAULT_WINDOW_GRACE_MINUTES = 30


def match_window(
    moment: datetime,
    windows: Iterable[ChurchService],
    grace_minutes: int = DEFAULT_WINDOW_GRACE_MINUTES,
) -> ChurchService | None:
    """Return the active window containing ``moment``, or ``None``.

    ``moment`` must already be in church-local time. The range is half-open —
    ``start_time`` is inside, the end is not — so back-to-back windows never both
    claim the same instant. When several match, the earliest-starting one wins,
    which keeps grouping deterministic under overlapping configuration.

    The end is extended by ``grace_minutes`` because services run long: a hymn sung
    at 21:10 in a service scheduled to 21:00 is still that service. The start is
    *not* extended — someone opening a hymn before the service begins is preparing,
    not singing with the congregation.

    The comparison is done on datetimes rather than times so a grace period crossing
    midnight does not wrap around and silently stop matching.

    >>> match_window(local_sunday_evening, windows)
    <ChurchService: Culto Dominical (6 19:30:00-21:00:00)>
    """
    naive = moment.replace(tzinfo=None)
    grace = timedelta(minutes=grace_minutes)

    candidates = [
        window
        for window in windows
        if window.weekday == from_python_weekday(moment.weekday())
        and datetime.combine(naive.date(), window.start_time)
        <= naive
        < datetime.combine(naive.date(), window.end_time) + grace
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda w: w.start_time)


def bucket_label(occurred_on: date, window_id: int | None, group_by: str) -> str:
    """Return the grouping label for an occurrence.

    Grouping only changes this label — it never changes how occurrences collapse.

    >>> bucket_label(date(2026, 8, 9), 3, "service")
    '2026-08-09:3'
    >>> bucket_label(date(2026, 8, 9), None, "week")
    '2026-W32'
    """
    if group_by == GROUP_BY_DAY:
        return occurred_on.isoformat()
    if group_by == GROUP_BY_WEEK:
        iso_year, iso_week, _ = occurred_on.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if group_by == GROUP_BY_MONTH:
        return f"{occurred_on.year}-{occurred_on.month:02d}"
    # GROUP_BY_SERVICE
    suffix = str(window_id) if window_id is not None else NO_WINDOW_BUCKET_SUFFIX
    return f"{occurred_on.isoformat()}:{suffix}"


def group_events(
    events: Iterable[tuple[int, datetime, str]],
    windows: Iterable[ChurchService],
    grace_minutes: int = DEFAULT_WINDOW_GRACE_MINUTES,
) -> dict[OccurrenceKey, set[str]]:
    """Collapse raw (hymn_id, viewed_at, device_id) rows into occurrence keys.

    The value is the set of devices that contributed, which becomes ``device_count``.

    >>> group_events([(1, moment, "dev-a"), (1, moment, "dev-b")], windows)
    {(1, 3, datetime.date(2026, 8, 9)): {'dev-a', 'dev-b'}}
    """
    window_list = list(windows)
    grouped: dict[OccurrenceKey, set[str]] = {}

    for hymn_id, viewed_at, device_id in events:
        local = timezone.localtime(viewed_at)
        window = match_window(local, window_list, grace_minutes)
        key: OccurrenceKey = (hymn_id, window.id if window else None, local.date())
        grouped.setdefault(key, set()).add(device_id)

    return grouped


def collapse_events(
    events: Iterable[tuple[int, datetime, str]],
    windows: Iterable[ChurchService],
    hymn_labels: dict[int, tuple[str, str]],
    group_by: str = GROUP_BY_SERVICE,
    grace_minutes: int = DEFAULT_WINDOW_GRACE_MINUTES,
) -> list[OccurrenceDTO]:
    """Turn raw view rows into ordered occurrences.

    Ordering is stable — date, then window start time (no-window last), then hymn
    number — so an identical request never reshuffles the chart.

    >>> collapse_events(rows, windows, {1: ("50", "Grandioso És Tu")}, "service")
    [OccurrenceDTO(hymn_number='50', ...)]
    """
    window_list = list(windows)
    windows_by_id = {w.id: w for w in window_list}
    grouped = group_events(events, window_list, grace_minutes)

    occurrences = [
        OccurrenceDTO(
            hymn_number=hymn_labels.get(hymn_id, ("", ""))[0],
            hymn_title=hymn_labels.get(hymn_id, ("", ""))[1],
            occurred_on=occurred_on,
            service_window_id=window_id,
            service_window_name=(
                windows_by_id[window_id].name if window_id in windows_by_id else None
            ),
            bucket=bucket_label(occurred_on, window_id, group_by),
            device_count=len(devices),
        )
        for (hymn_id, window_id, occurred_on), devices in grouped.items()
    ]

    return sorted(occurrences, key=_occurrence_sort_key(windows_by_id))


def _occurrence_sort_key(
    windows_by_id: dict[int, ChurchService],
) -> Callable[[OccurrenceDTO], tuple[date, int, str, tuple[int, str]]]:
    """Build the stable ordering key: date, window start (nulls last), hymn number."""

    def key(occurrence: OccurrenceDTO) -> tuple[date, int, str, tuple[int, str]]:
        window_id = occurrence.service_window_id
        if window_id is not None and window_id in windows_by_id:
            start = windows_by_id[window_id].start_time.isoformat()
            has_no_window = 0
        else:
            start = ""
            has_no_window = 1
        return (
            occurrence.occurred_on,
            has_no_window,
            start,
            hymn_sort_key(occurrence.hymn_number),
        )

    return key
