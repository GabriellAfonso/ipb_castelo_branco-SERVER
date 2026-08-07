from django.contrib import admin

from features.schedule.models.schedule import MemberScheduleConfig, MonthlySchedule

# ChurchService (formerly ScheduleType) is registered by core, which now owns it.

admin.site.register([MemberScheduleConfig])


@admin.register(MonthlySchedule)
class MonthlyScheduleAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    readonly_fields = ("created_at",)
    fields = (
        "date",
        "schedule_type",
        "member",
        "created_at",
    )
