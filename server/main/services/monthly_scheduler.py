import random
import calendar
from collections import defaultdict
from datetime import date

from django.db import transaction

from main.models.schedule import (
    ScheduleType,
    MemberScheduleConfig,
    MonthlySchedule,
)


WEEKDAYS_MAP = {
    1: calendar.SUNDAY,
    3: calendar.TUESDAY,
    5: calendar.THURSDAY,
}


def generate_monthly_schedule():
    today = date.today()
    year = today.year
    month = today.month

    _, last_day = calendar.monthrange(year, month)

    MonthlySchedule.objects.filter(year=year, month=month).delete()

    # contador global por membro (evita repetir entre dias e tipos)
    usage_count = defaultdict(int)

    for schedule_type in ScheduleType.objects.all():
        if schedule_type.weekday not in WEEKDAYS_MAP:
            continue

        target_weekday = WEEKDAYS_MAP[schedule_type.weekday]

        dates = [
            date(year, month, day)
            for day in range(1, last_day + 1)
            if date(year, month, day).weekday() == target_weekday
        ]

        configs = list(
            MemberScheduleConfig.objects.filter(
                schedule_type=schedule_type,
                available=True
            )
        )

        if not configs:
            continue

        # pool ponderado
        weighted_members = []
        for cfg in configs:
            weighted_members.extend([cfg.member] * cfg.weight)

        random.shuffle(weighted_members)

        with transaction.atomic():
            for d in dates:
                # tenta quem nunca foi usado
                unused = [
                    m for m in weighted_members
                    if usage_count[m.id] == 0
                ]

                if unused:
                    member = unused[0]
                else:
                    # todos já usados → pega quem menos trabalhou
                    member = min(
                        weighted_members,
                        key=lambda m: usage_count[m.id]
                    )

                usage_count[member.id] += 1
                weighted_members.remove(member)

                MonthlySchedule.objects.create(
                    date=d,
                    schedule_type=schedule_type,
                    member=member
                )
