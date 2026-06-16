from collections import defaultdict
from datetime import date
from typing import Any

from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.http.permissions import IsAdminUser, IsMemberUser
from core.http.utils import _not_modified_or_response
from features.schedule.models.schedule import MonthlySchedule
from features.schedule.services.monthly_scheduler import (
    generate_monthly_schedule_preview,
    save_monthly_schedule,
)


def _group_monthly_schedule_qs(schedules: QuerySet[MonthlySchedule]) -> dict[str, Any]:
    grouped: dict[str, Any] = defaultdict(lambda: {"time": None, "items": []})

    for s in schedules:
        key = s.schedule_type.name
        grouped[key]["time"] = s.schedule_type.time.strftime("%H:%M")
        grouped[key]["items"].append(
            {
                "date": s.date.isoformat(),
                "day": s.date.day,
                "member": {"id": s.member_id, "name": s.member.name},
                "schedule_type": {"id": s.schedule_type_id, "name": s.schedule_type.name},
            }
        )

    return grouped


class CurrentMonthlyScheduleAPI(APIView):
    permission_classes = [IsMemberUser]

    @staticmethod
    def get(request: Request) -> Response:
        today = date.today()

        schedules = (
            MonthlySchedule.objects.filter(year=today.year, month=today.month)
            .select_related("member", "schedule_type")
            .order_by("schedule_type__name", "date")
        )

        result = {
            "year": today.year,
            "month": today.month,
            "schedule": _group_monthly_schedule_qs(schedules),
        }
        return _not_modified_or_response(request, result, status_code=200)


class MonthlySchedulePreviewAPI(APIView):
    """
    POST body example:
    {
      "year": 2026,
      "month": 3,
      "fixed": [
        {"schedule_type_id": 1, "date": "2026-03-02", "member_id": 10},
        {"schedule_type_id": 2, "date": "2026-03-09", "member_id": 5}
      ]
    }

    If year/month omitted -> defaults to next month.
    """

    permission_classes = [IsAdminUser]

    def post(self, request: Request) -> Response:
        year = request.data.get("year")
        month = request.data.get("month")
        fixed_list = request.data.get("fixed", []) or []

        fixed_map: dict[tuple[int, date], int] = {}
        for f in fixed_list:
            try:
                schedule_type_id = int(f["schedule_type_id"])
                d = date.fromisoformat(f["date"])
                member_id = int(f["member_id"])
            except (KeyError, ValueError, TypeError):
                continue
            fixed_map[(schedule_type_id, d)] = member_id

        preview = generate_monthly_schedule_preview(
            year=int(year) if year is not None else None,
            month=int(month) if month is not None else None,
            fixed=fixed_map,
        )
        return Response(preview, status=200)


class MonthlyScheduleSaveAPI(APIView):
    """
    POST body example:
    {
      "year": 2026,
      "month": 3,
      "items": [
        {"date":"2026-03-02","schedule_type_id":1,"member_id":10},
        {"date":"2026-03-09","schedule_type_id":1,"member_id":11}
      ]
    }
    """

    permission_classes = [IsAdminUser]

    def post(self, request: Request) -> Response:
        # ValidationError and ScheduleOverwriteError bubble up to custom_exception_handler
        year, month, normalized = _parse_schedule_save_payload(request.data)
        save_monthly_schedule(year=year, month=month, items=normalized)
        return Response({"ok": True}, status=200)


def _parse_schedule_save_payload(
    data: dict[str, Any],
) -> tuple[int, int, list[dict[str, Any]]]:
    """Extract and validate schedule save payload.

    Raises ``ValidationError`` on invalid input.
    """
    from core.domain.exceptions import ValidationError

    raw_year = data.get("year")
    raw_month = data.get("month")

    if raw_year is None or raw_month is None:
        raise ValidationError("Fields 'year' and 'month' are required.")

    try:
        year = int(raw_year)
        month = int(raw_month)
    except (TypeError, ValueError):
        raise ValidationError("Fields 'year' and 'month' must be integers.")

    items = data.get("items", []) or []

    normalized: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if "schedule_type_id" in it and "member_id" in it:
            normalized.append(it)
            continue
        try:
            normalized.append(
                {
                    "date": it["date"],
                    "schedule_type_id": it["schedule_type"]["id"],
                    "member_id": it["member"]["id"],
                }
            )
        except (KeyError, TypeError):
            continue

    return year, month, normalized
