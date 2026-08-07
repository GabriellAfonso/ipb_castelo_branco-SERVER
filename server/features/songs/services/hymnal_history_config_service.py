"""Configuration use cases: collection settings and service windows."""

from typing import Any

from core.domain.exceptions import ServiceWindowNotFoundError
from features.songs.hymnal_history_dtos import HymnalHistorySettingsDTO, ServiceWindowDTO
from features.songs.models.hymnal_history import HymnalHistorySettings, ServiceWindow
from features.songs.repositories.interfaces import HymnalHistoryRepository

SETTINGS_FIELDS = (
    "min_seconds_to_count",
    "collapse_window_minutes",
    "max_batch_size",
    "max_past_days",
    "future_tolerance_minutes",
    "window_grace_minutes",
)


class HymnalHistoryConfigService:
    """Reads and updates the tunables an admin owns.

    Changing anything here affects future behaviour only — no stored event is ever
    rewritten, re-evaluated or deleted.
    """

    def __init__(self, repository: HymnalHistoryRepository) -> None:
        self._repository = repository

    def get_settings(self) -> HymnalHistorySettingsDTO:
        """Return the singleton settings, materialising defaults on first read.

        >>> service.get_settings()
        HymnalHistorySettingsDTO(min_seconds_to_count=30, ...)
        """
        return self._to_settings_dto(self._repository.get_settings())

    def update_settings(self, changes: dict[str, int]) -> HymnalHistorySettingsDTO:
        """Apply a partial update to the settings singleton.

        >>> service.update_settings({"min_seconds_to_count": 45})
        HymnalHistorySettingsDTO(min_seconds_to_count=45, ...)
        """
        allowed = {k: v for k, v in changes.items() if k in SETTINGS_FIELDS}
        return self._to_settings_dto(self._repository.update_settings(allowed))

    def list_windows(self) -> list[ServiceWindowDTO]:
        """Return every service window, ordered by weekday then start time."""
        return [self._to_window_dto(w) for w in self._repository.list_service_windows()]

    def get_window(self, window_id: int) -> ServiceWindowDTO:
        """Return one service window.

        Raises ``ServiceWindowNotFoundError`` when the id does not exist.
        """
        return self._to_window_dto(self._require_window(window_id))

    def create_window(self, data: ServiceWindowDTO) -> ServiceWindowDTO:
        """Create a service window.

        >>> service.create_window(ServiceWindowDTO(name="Culto", weekday=6, ...))
        ServiceWindowDTO(id=1, name='Culto', weekday=6, ...)
        """
        return self._to_window_dto(self._repository.create_service_window(data))

    def update_window(self, window_id: int, changes: dict[str, Any]) -> ServiceWindowDTO:
        """Apply a partial update to a service window.

        Never touches stored events: occurrences are derived at read time, so the
        next report simply reflects the new configuration.
        """
        window = self._require_window(window_id)
        return self._to_window_dto(self._repository.update_service_window(window, changes))

    def delete_window(self, window_id: int) -> None:
        """Delete a service window, leaving every stored view event intact."""
        self._repository.delete_service_window(self._require_window(window_id))

    def _require_window(self, window_id: int) -> ServiceWindow:
        window = self._repository.get_service_window(window_id)
        if window is None:
            raise ServiceWindowNotFoundError(window_id)
        return window

    def _to_settings_dto(self, row: HymnalHistorySettings) -> HymnalHistorySettingsDTO:
        return HymnalHistorySettingsDTO(
            min_seconds_to_count=row.min_seconds_to_count,
            collapse_window_minutes=row.collapse_window_minutes,
            max_batch_size=row.max_batch_size,
            max_past_days=row.max_past_days,
            future_tolerance_minutes=row.future_tolerance_minutes,
            window_grace_minutes=row.window_grace_minutes,
        )

    def _to_window_dto(self, window: ServiceWindow) -> ServiceWindowDTO:
        return ServiceWindowDTO(
            id=window.id,
            name=window.name,
            weekday=window.weekday,
            start_time=window.start_time,
            end_time=window.end_time,
            active=window.active,
        )
