from collections import defaultdict
from datetime import date

from rest_framework.views import APIView

from main.models.schedule import MonthlySchedule
from main.services.monthly_scheduler import generate_monthly_schedule

from .utils import _not_modified_or_response


class GenerateMonthlyScheduleAPI(APIView):
    def post(self, request):
        generate_monthly_schedule()

        today = date.today()

        schedules = (
            MonthlySchedule.objects.filter(year=today.year, month=today.month)
            .select_related("member", "schedule_type")
            .order_by("schedule_type__name", "date")
        )

        grouped = defaultdict(lambda: {"time": None, "items": []})

        for s in schedules:
            key = s.schedule_type.name
            grouped[key]["time"] = s.schedule_type.time.strftime("%H:%M")
            grouped[key]["items"].append(
                {"day": s.date.day, "member": s.member.name}
            )

        result = {"year": today.year,
                  "month": today.month, "schedule": grouped}
        return _not_modified_or_response(request, result, status_code=200)
