from datetime import datetime
from typing import Any

from django.db import transaction

from core.models import ChurchService
from features.schedule.dtos import MemberConfigDTO, MonthlyScheduleDTO, ScheduleTypeDTO
from features.schedule.models.schedule import (
    MemberScheduleConfig,
    MonthlySchedule,
)


class ScheduleRepositoryImpl:
    def list_schedule_types(self) -> list[ScheduleTypeDTO]:
        return [
            ScheduleTypeDTO(
                id=service.id,
                name=service.name,
                weekday=service.weekday,
                # `time` keeps its DTO name: it is what the rota response exposes.
                time=service.start_time,
                end_time=service.end_time,
                active=service.active,
                takes_rota=service.takes_rota,
            )
            for service in ChurchService.objects.all()
        ]

    def list_available_configs(self, schedule_type_id: int) -> list[MemberConfigDTO]:
        configs = MemberScheduleConfig.objects.filter(
            schedule_type_id=schedule_type_id,
            available=True,
        ).select_related("member")
        return [
            MemberConfigDTO(
                member_id=cfg.member_id,
                member_name=cfg.member.name,
                weight=cfg.weight,
            )
            for cfg in configs
        ]

    def list_monthly_schedules(self, year: int, month: int) -> list[MonthlyScheduleDTO]:
        schedules = (
            MonthlySchedule.objects.filter(year=year, month=month)
            .select_related("member", "schedule_type")
            .order_by("schedule_type__name", "date")
        )
        return [
            MonthlyScheduleDTO(
                date=s.date,
                member_id=s.member_id,
                member_name=s.member.name,
                schedule_type_id=s.schedule_type_id,
                schedule_type_name=s.schedule_type.name,
                schedule_type_time=s.schedule_type.start_time,
            )
            for s in schedules
        ]

    def get_earliest_created_at(self, year: int, month: int) -> datetime | None:
        return (
            MonthlySchedule.objects.filter(year=year, month=month)
            .order_by("created_at")
            .values_list("created_at", flat=True)
            .first()
        )

    @transaction.atomic
    def replace_schedules(self, year: int, month: int, items: list[dict[str, Any]]) -> None:
        from datetime import date

        MonthlySchedule.objects.filter(year=year, month=month).delete()

        to_create = [
            MonthlySchedule(
                date=date.fromisoformat(it["date"]),
                year=date.fromisoformat(it["date"]).year,
                month=date.fromisoformat(it["date"]).month,
                schedule_type_id=int(it["schedule_type_id"]),
                member_id=int(it["member_id"]),
            )
            for it in items
        ]
        MonthlySchedule.objects.bulk_create(to_create)
