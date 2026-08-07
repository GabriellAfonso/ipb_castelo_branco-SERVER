"""DTOs crossing the layer boundaries of the hymnal view history feature.

Kept beside ``dtos.py`` rather than inside it: that module belongs to the Sunday
plays flow, and mixing telemetry DTOs in would break its single responsibility.
"""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import field_validator

from core.application.dtos.strict_base import StrictBaseModel

# Rejection reason codes. Stable API surface — the app logs and switches on these,
# so changing one is a breaking change for the client.
REASON_UNKNOWN_HYMN = "unknown_hymn"
REASON_VIEWED_AT_IN_FUTURE = "viewed_at_in_future"
REASON_VIEWED_AT_TOO_OLD = "viewed_at_too_old"
REASON_INVALID_EVENT = "invalid_event"

GROUP_BY_SERVICE = "service"
GROUP_BY_DAY = "day"
GROUP_BY_WEEK = "week"
GROUP_BY_MONTH = "month"
GROUP_BY_CHOICES = (GROUP_BY_SERVICE, GROUP_BY_DAY, GROUP_BY_WEEK, GROUP_BY_MONTH)


class HymnViewEventInput(StrictBaseModel):
    """One hymn view submitted by the app."""

    client_event_id: UUID
    hymn_id: int
    device_id: str
    viewed_at: datetime
    duration_seconds: int
    app_version: str = ""
    platform: str = ""

    @field_validator("viewed_at")
    @classmethod
    def must_be_aware(cls, value: datetime) -> datetime:
        """A naive timestamp cannot be placed in a service window without guessing."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"viewed_at must include a UTC offset, got '{value.isoformat()}'")
        return value

    @field_validator("duration_seconds")
    @classmethod
    def must_not_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError(f"duration_seconds must be >= 0, got {value}")
        return value

    @field_validator("device_id")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("device_id must be a non-empty string")
        return cleaned


class RejectedEventDTO(StrictBaseModel):
    """An event the backend refused, with the reason the app should log."""

    client_event_id: UUID
    reason: str


class IngestResultDTO(StrictBaseModel):
    """Outcome of one ingest batch.

    Everything in ``accepted`` is safe for the app to delete locally, whether it
    was stored, deduplicated or collapsed.
    """

    accepted: list[UUID]
    rejected: list[RejectedEventDTO]


class OccurrenceDTO(StrictBaseModel):
    """One hymn sung once by the congregation. Derived at read time, never stored."""

    hymn_number: str
    hymn_title: str
    occurred_on: date
    service_window_id: int | None
    service_window_name: str | None
    bucket: str
    device_count: int


class TopHymnDTO(StrictBaseModel):
    """A hymn and how many occurrences it has in the requested range."""

    hymn_number: str
    hymn_title: str
    occurrence_count: int


class HymnalHistorySettingsDTO(StrictBaseModel):
    """The tunable collection settings."""

    min_seconds_to_count: int
    collapse_window_minutes: int
    max_batch_size: int
    max_past_days: int
    future_tolerance_minutes: int
    window_grace_minutes: int


class ServiceWindowDTO(StrictBaseModel):
    """A recurring church service window. Weekday is 0=Monday ... 6=Sunday."""

    id: int | None = None
    name: str
    weekday: int
    start_time: time
    end_time: time
    active: bool = True


class ReportRangeDTO(StrictBaseModel):
    """An inclusive local-date range plus the requested grouping."""

    from_date: date
    to_date: date
    group_by: str = GROUP_BY_SERVICE
