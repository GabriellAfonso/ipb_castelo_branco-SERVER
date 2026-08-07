"""Seed the church's current service windows.

Reason: occurrence reporting groups hymn views by service window. With the table
empty every view collapses by hymn + calendar day, so the dashboard works but
cannot tell a Sunday morning from a Sunday evening. These are the church's actual
service times as of 2026-08-07, confirmed by the church, so the feature is
meaningful from the first deploy instead of waiting on manual setup.

Weekday convention is Python's ``datetime.weekday()``: 0 = Monday ... 6 = Sunday.
Sunday is 6, not 0. Getting this wrong fails silently — the window simply never
matches and views quietly fall back to day-collapsing.

End times are the *scheduled* end. Matching extends past it by
``HymnalHistorySettings.window_grace_minutes`` (default 30) so a hymn sung in a
service that runs long still belongs to that service.

Reverse deletes exactly these four rows by name, leaving anything an admin added
later untouched.
"""

from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)

SERVICE_WINDOWS = [
    {
        "name": "Terça de Oração",
        "weekday": TUESDAY,
        "start_time": "19:30",
        "end_time": "20:30",
    },
    {
        "name": "Quinta de Oração",
        "weekday": THURSDAY,
        "start_time": "19:30",
        "end_time": "20:30",
    },
    {
        "name": "Escola Bíblica Dominical",
        "weekday": SUNDAY,
        "start_time": "09:00",
        "end_time": "10:00",
    },
    {
        "name": "Culto Dominical",
        "weekday": SUNDAY,
        "start_time": "19:30",
        "end_time": "21:00",
    },
]


def seed_service_windows(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    ServiceWindow = apps.get_model("songs", "ServiceWindow")
    for window in SERVICE_WINDOWS:
        # get_or_create keeps the migration safe to re-run and avoids clobbering a
        # window an admin already created with the same name.
        ServiceWindow.objects.get_or_create(
            name=window["name"],
            defaults={
                "weekday": window["weekday"],
                "start_time": window["start_time"],
                "end_time": window["end_time"],
                "active": True,
            },
        )


def remove_service_windows(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    ServiceWindow = apps.get_model("songs", "ServiceWindow")
    ServiceWindow.objects.filter(name__in=[w["name"] for w in SERVICE_WINDOWS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("songs", "0005_hymnalhistorysettings_window_grace_minutes"),
    ]

    operations = [
        migrations.RunPython(seed_service_windows, remove_service_windows),
    ]
