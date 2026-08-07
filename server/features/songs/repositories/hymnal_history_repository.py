"""The only place the hymnal view history feature touches the ORM."""

from datetime import datetime
from typing import Any
from uuid import UUID

from django.db.models import Q

from features.songs.hymnal_history_dtos import ServiceWindowDTO
from features.songs.models.hymnal import Hymn
from features.songs.models.hymnal_history import (
    HymnalHistorySettings,
    HymnalViewEvent,
    ServiceWindow,
)

SETTINGS_ROW_ID = 1


class DjangoHymnalHistoryRepository:
    """Hymnal view history repository using Django ORM.

    Reads are deliberately bulk: an ingest batch of any size costs a constant
    number of queries.
    """

    def get_existing_client_event_ids(self, client_event_ids: list[UUID]) -> set[UUID]:
        """Return the subset of ids already stored.

        >>> repo.get_existing_client_event_ids([UUID("...")])
        {UUID('...')}
        """
        if not client_event_ids:
            return set()
        rows = HymnalViewEvent.objects.filter(client_event_id__in=client_event_ids).values_list(
            "client_event_id", flat=True
        )
        return set(rows)

    def get_collapse_candidates(
        self,
        pairs: set[tuple[int, str]],
        window_start: datetime,
        window_end: datetime,
    ) -> list[tuple[int, str, datetime]]:
        """Return stored (hymn_id, device_id, viewed_at) rows that could collapse a new event.

        One query for the whole batch: filtered to the batch's hymn/device pairs and
        bounded by the widest interval any event in the batch could collapse against.

        >>> repo.get_collapse_candidates({(1, "dev-a")}, start, end)
        [(1, 'dev-a', datetime.datetime(...))]
        """
        if not pairs:
            return []

        pair_filter = Q()
        for hymn_id, device_id in pairs:
            pair_filter |= Q(hymn_id=hymn_id, device_id=device_id)

        rows = (
            HymnalViewEvent.objects.filter(pair_filter)
            .filter(viewed_at__gte=window_start, viewed_at__lte=window_end)
            .values_list("hymn_id", "device_id", "viewed_at")
        )
        return list(rows)

    def get_existing_hymn_ids(self, hymn_ids: set[int]) -> set[int]:
        """Return the subset of hymn ids that exist."""
        if not hymn_ids:
            return set()
        return set(Hymn.objects.filter(id__in=hymn_ids).values_list("id", flat=True))

    def bulk_create_events(self, events: list[HymnalViewEvent]) -> None:
        """Insert events, ignoring unique-constraint conflicts.

        ``ignore_conflicts`` is the race guard: two concurrent syncs of the same
        batch both pass the pre-check, and the loser becomes a silent no-op instead
        of a 500. The row exists either way, so both requests report it accepted.
        """
        if not events:
            return
        HymnalViewEvent.objects.bulk_create(events, ignore_conflicts=True)

    def list_events_in_range(
        self,
        start: datetime | None,
        end: datetime | None,
    ) -> list[tuple[int, datetime, str]]:
        """Return raw (hymn_id, viewed_at, device_id) rows for occurrence collapsing.

        Returns tuples rather than model instances: reporting never needs the
        objects, and this keeps a full-year range cheap.

        >>> repo.list_events_in_range(start, end)
        [(1, datetime.datetime(...), 'dev-a'), ...]
        """
        qs = HymnalViewEvent.objects.all()
        if start is not None:
            qs = qs.filter(viewed_at__gte=start)
        if end is not None:
            qs = qs.filter(viewed_at__lt=end)
        return list(qs.values_list("hymn_id", "viewed_at", "device_id"))

    def get_hymn_labels(self, hymn_ids: set[int]) -> dict[int, tuple[str, str]]:
        """Map hymn id to (number, title) for the hymns referenced by a report."""
        if not hymn_ids:
            return {}
        rows = Hymn.objects.filter(id__in=hymn_ids).values_list("id", "number", "title")
        return {pk: (number, title) for pk, number, title in rows}

    def list_active_service_windows(self) -> list[ServiceWindow]:
        """Return active windows ordered by weekday then start time.

        The ordering is behaviour, not cosmetics: it decides which window wins
        when two overlap.
        """
        return list(ServiceWindow.objects.filter(active=True))

    def list_service_windows(self) -> list[ServiceWindow]:
        return list(ServiceWindow.objects.all())

    def get_service_window(self, window_id: int) -> ServiceWindow | None:
        return ServiceWindow.objects.filter(id=window_id).first()

    def create_service_window(self, data: ServiceWindowDTO) -> ServiceWindow:
        return ServiceWindow.objects.create(
            name=data.name,
            weekday=data.weekday,
            start_time=data.start_time,
            end_time=data.end_time,
            active=data.active,
        )

    def update_service_window(
        self,
        window: ServiceWindow,
        changes: dict[str, Any],
    ) -> ServiceWindow:
        for field, value in changes.items():
            setattr(window, field, value)
        window.save(update_fields=list(changes.keys()))
        return window

    def delete_service_window(self, window: ServiceWindow) -> None:
        window.delete()

    def get_settings(self) -> HymnalHistorySettings:
        """Return the singleton, materialising the defaults on first read.

        Means a fresh database serves working defaults without a data migration.
        """
        row, _ = HymnalHistorySettings.objects.get_or_create(id=SETTINGS_ROW_ID)
        return row

    def update_settings(self, changes: dict[str, int]) -> HymnalHistorySettings:
        row = self.get_settings()
        if not changes:
            return row
        for field, value in changes.items():
            setattr(row, field, value)
        row.save(update_fields=list(changes.keys()))
        return row
