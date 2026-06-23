from __future__ import annotations

from datetime import date, time

from features.schedule.dtos import MonthlyScheduleDTO
from features.schedule.services.schedule_service import _group_schedules


def _make_schedule_dto(
    type_name: str, type_time: time, d: date, member_id: int, member_name: str
) -> MonthlyScheduleDTO:
    return MonthlyScheduleDTO(
        date=d,
        member_id=member_id,
        member_name=member_name,
        schedule_type_id=1,
        schedule_type_name=type_name,
        schedule_type_time=type_time,
    )


class TestGroupSchedules:
    def test_groups_by_schedule_type_name(self) -> None:
        s1 = _make_schedule_dto("Culto", time(9, 0), date(2026, 5, 3), 1, "Alice")
        s2 = _make_schedule_dto("Culto", time(9, 0), date(2026, 5, 10), 2, "Bob")
        s3 = _make_schedule_dto("EBD", time(10, 0), date(2026, 5, 3), 3, "Carol")

        result = _group_schedules([s1, s2, s3])

        assert "Culto" in result
        assert "EBD" in result
        assert len(result["Culto"]["items"]) == 2
        assert len(result["EBD"]["items"]) == 1

    def test_time_formatted_as_hh_mm(self) -> None:
        s = _make_schedule_dto("Culto", time(9, 0), date(2026, 5, 3), 1, "Alice")

        result = _group_schedules([s])

        assert result["Culto"]["time"] == "09:00"

    def test_item_structure(self) -> None:
        s = _make_schedule_dto("Culto", time(9, 0), date(2026, 5, 3), 1, "Alice")

        result = _group_schedules([s])
        item = result["Culto"]["items"][0]

        assert item["date"] == "2026-05-03"
        assert item["day"] == 3
        assert item["member"] == {"id": 1, "name": "Alice"}
        assert item["schedule_type"]["name"] == "Culto"

    def test_empty_list_returns_empty_dict(self) -> None:
        result = _group_schedules([])
        assert dict(result) == {}
