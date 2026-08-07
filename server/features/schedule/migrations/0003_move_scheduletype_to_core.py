"""Hand off the service catalogue to core — state only, no database changes.

HAND-WRITTEN ON PURPOSE, and the twin of `core.0001_initial`. `makemigrations` would
express this as a plain DeleteModel, dropping `schedule_scheduletype` and every rota
row that references it. See specs/007-unify-service-catalogue/research.md R-02; the §5
exception is recorded in specs/constitution.md.

Two things happen, both in Django's state only:

1. `ScheduleType` leaves the schedule app. `core.ChurchService` already describes the
   same table, so the table itself is untouched.
2. The two foreign keys retarget from `schedule.ScheduleType` to `core.ChurchService`.
   The column stays `schedule_type_id`, the constraint already points at the right
   table, and the ids do not change — so there is nothing for the database to do.

The field names stay `schedule_type` deliberately: they are the wire format the Android
app sends and receives (research R-07).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("schedule", "0002_alter_memberscheduleconfig_schedule_type_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="memberscheduleconfig",
                    name="schedule_type",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="core.churchservice",
                    ),
                ),
                migrations.AlterField(
                    model_name="monthlyschedule",
                    name="schedule_type",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="core.churchservice",
                    ),
                ),
                migrations.DeleteModel(name="ScheduleType"),
            ],
        ),
    ]
