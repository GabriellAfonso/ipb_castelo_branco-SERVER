from datetime import datetime
from typing import Any, Protocol

from features.schedule.dtos import MemberConfigDTO, MonthlyScheduleDTO, ScheduleTypeDTO


class ScheduleRepository(Protocol):
    """Contract for schedule persistence operations."""

    def list_schedule_types(self) -> list[ScheduleTypeDTO]: ...

    def list_available_configs(self, schedule_type_id: int) -> list[MemberConfigDTO]: ...

    def list_monthly_schedules(self, year: int, month: int) -> list[MonthlyScheduleDTO]: ...

    def get_earliest_created_at(self, year: int, month: int) -> datetime | None: ...

    def replace_schedules(self, year: int, month: int, items: list[dict[str, Any]]) -> None: ...
