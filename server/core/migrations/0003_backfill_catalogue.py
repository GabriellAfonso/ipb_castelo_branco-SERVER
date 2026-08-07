"""Backfill the church's real service times and add Escola Bíblica Dominical.

Reason: `end_time` is new and required, and the three existing services only ever
stored a start time. These end times were confirmed by the church on 2026-08-07 and
are the same values feature 006 seeded on the hymnal side, so the two sources agree.

Escola Bíblica Dominical existed only on the hymnal side. It joins the shared
catalogue with `takes_rota=False`: it is held every Sunday morning and groups hymn
views, but nobody is rostered for it. Without that flag, unifying the catalogues
would silently start generating rota rows for Sunday mornings.

Weekday convention is `1 = Sunday … 7 = Saturday`, so Sunday is 1.

Matched by name rather than id so the migration is safe to re-run and does not
depend on ids that could differ in another environment. The reverse removes the EBD
row and nulls the added column, leaving the original three untouched.
"""

from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import F, Q

SUNDAY = 1

TUESDAY = 3
THURSDAY = 5

# The church's full schedule. In production the first three already exist as rows 1-3,
# so they are matched by name and only gain an end time — their ids never change. On a
# fresh database (tests, a new environment) all four are created.
SERVICES = [
    {
        "name": "Terça de Oração",
        "weekday": TUESDAY,
        "start_time": "19:30",
        "end_time": "20:30",
        "takes_rota": True,
    },
    {
        "name": "Quinta de Oração",
        "weekday": THURSDAY,
        "start_time": "19:30",
        "end_time": "20:30",
        "takes_rota": True,
    },
    {
        "name": "Domingo Liturgia de Adoração",
        "weekday": SUNDAY,
        "start_time": "19:30",
        "end_time": "21:00",
        "takes_rota": True,
    },
    # Held every Sunday morning, and nobody is rostered for it.
    {
        "name": "Escola Bíblica Dominical",
        "weekday": SUNDAY,
        "start_time": "09:00",
        "end_time": "10:00",
        "takes_rota": False,
    },
]

# A service the church added without an end time would fail the NOT NULL below.
FALLBACK_END_TIME = "20:30"


def backfill(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    ChurchService = apps.get_model("core", "ChurchService")

    for service in SERVICES:
        existing = ChurchService.objects.filter(name=service["name"]).first()
        if existing is None:
            ChurchService.objects.create(
                name=service["name"],
                weekday=service["weekday"],
                start_time=service["start_time"],
                end_time=service["end_time"],
                active=True,
                takes_rota=service["takes_rota"],
            )
            continue
        # Existing production row: give it the missing end time and nothing else.
        # Its weekday, start time and id are already correct and must not move.
        if existing.end_time is None:
            existing.end_time = service["end_time"]
            existing.takes_rota = service["takes_rota"]
            existing.save(update_fields=["end_time", "takes_rota"])

    ChurchService.objects.filter(end_time__isnull=True).update(end_time=FALLBACK_END_TIME)


def undo_backfill(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    ChurchService = apps.get_model("core", "ChurchService")
    ChurchService.objects.filter(name="Escola Bíblica Dominical").delete()
    ChurchService.objects.update(end_time=None)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_rename_and_extend"),
    ]

    operations = [
        migrations.RunPython(backfill, undo_backfill),
        migrations.AlterField(
            model_name="churchservice",
            name="end_time",
            field=models.TimeField(),
        ),
        migrations.AddConstraint(
            model_name="churchservice",
            constraint=models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="church_service_end_after_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="churchservice",
            constraint=models.CheckConstraint(
                condition=Q(weekday__gte=1) & Q(weekday__lte=7),
                name="church_service_weekday_range",
            ),
        ),
    ]
