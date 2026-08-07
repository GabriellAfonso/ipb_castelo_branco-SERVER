"""Named test doubles for the hymnal view history feature.

Named classes rather than inline stubs, per CLAUDE.md §10.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from features.songs.hymnal_history_dtos import ServiceWindowDTO
from features.songs.models.hymnal_history import (
    HymnalHistorySettings,
    HymnalViewEvent,
    ServiceWindow,
)


class FrozenClock:
    """Clock that always returns the same instant, so time-based rules are testable."""

    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


class FakeHymnalHistoryRepository:
    """In-memory implementation of ``HymnalHistoryRepository``.

    Holds unsaved model instances; nothing here touches the database.
    """

    def __init__(
        self,
        stored_events: list[HymnalViewEvent] | None = None,
        hymn_ids: set[int] | None = None,
        windows: list[ServiceWindow] | None = None,
        settings: HymnalHistorySettings | None = None,
        hymn_labels: dict[int, tuple[str, str]] | None = None,
    ) -> None:
        self.stored_events = stored_events or []
        self.hymn_ids = hymn_ids or set()
        self.windows = windows or []
        self.settings = settings or HymnalHistorySettings(id=1)
        self.hymn_labels = hymn_labels or {}
        self.created_events: list[HymnalViewEvent] = []
        self.deleted_windows: list[ServiceWindow] = []

    def get_existing_client_event_ids(self, client_event_ids: list[UUID]) -> set[UUID]:
        wanted = set(client_event_ids)
        return {e.client_event_id for e in self.stored_events if e.client_event_id in wanted}

    def get_collapse_candidates(
        self,
        pairs: set[tuple[int, str]],
        window_start: datetime,
        window_end: datetime,
    ) -> list[tuple[int, str, datetime]]:
        return [
            (e.hymn_id, e.device_id, e.viewed_at)
            for e in self.stored_events
            if (e.hymn_id, e.device_id) in pairs and window_start <= e.viewed_at <= window_end
        ]

    def get_existing_hymn_ids(self, hymn_ids: set[int]) -> set[int]:
        return hymn_ids & self.hymn_ids

    def bulk_create_events(self, events: list[HymnalViewEvent]) -> None:
        self.created_events.extend(events)
        self.stored_events.extend(events)

    def list_events_in_range(
        self,
        start: datetime | None,
        end: datetime | None,
    ) -> list[tuple[int, datetime, str]]:
        rows = []
        for event in self.stored_events:
            if start is not None and event.viewed_at < start:
                continue
            if end is not None and event.viewed_at >= end:
                continue
            rows.append((event.hymn_id, event.viewed_at, event.device_id))
        return rows

    def get_hymn_labels(self, hymn_ids: set[int]) -> dict[int, tuple[str, str]]:
        return {pk: label for pk, label in self.hymn_labels.items() if pk in hymn_ids}

    def list_active_service_windows(self) -> list[ServiceWindow]:
        return [w for w in self.windows if w.active]

    def list_service_windows(self) -> list[ServiceWindow]:
        return list(self.windows)

    def get_service_window(self, window_id: int) -> ServiceWindow | None:
        return next((w for w in self.windows if w.id == window_id), None)

    def create_service_window(self, data: ServiceWindowDTO) -> ServiceWindow:
        window = ServiceWindow(
            id=len(self.windows) + 1,
            name=data.name,
            weekday=data.weekday,
            start_time=data.start_time,
            end_time=data.end_time,
            active=data.active,
        )
        self.windows.append(window)
        return window

    def update_service_window(
        self,
        window: ServiceWindow,
        changes: dict[str, Any],
    ) -> ServiceWindow:
        for field, value in changes.items():
            setattr(window, field, value)
        return window

    def delete_service_window(self, window: ServiceWindow) -> None:
        self.windows = [w for w in self.windows if w.id != window.id]
        self.deleted_windows.append(window)

    def get_settings(self) -> HymnalHistorySettings:
        return self.settings

    def update_settings(self, changes: dict[str, int]) -> HymnalHistorySettings:
        for field, value in changes.items():
            setattr(self.settings, field, value)
        return self.settings
