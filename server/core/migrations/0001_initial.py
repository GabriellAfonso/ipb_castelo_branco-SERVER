"""Take ownership of the church service catalogue — state only, no database changes.

HAND-WRITTEN ON PURPOSE. `makemigrations` cannot express this and must never be used
to regenerate it: it sees a model moving between apps as an unrelated DeleteModel plus
CreateModel, which would DROP `schedule_scheduletype` and take every rota row with it.
See specs/007-unify-service-catalogue/research.md R-02. The §5 exception for this
migration is recorded in specs/constitution.md.

`SeparateDatabaseAndState` with no `database_operations` tells Django "the table already
exists and already looks like this — just change which app owns the model". Nothing is
created, altered, copied or renumbered. The ids the Android app caches stay valid.

The field list below is deliberately identical to `schedule.ScheduleType` as it stood
before this migration, and `db_table` keeps the original name. The new columns and the
table rename arrive in 0002, after this move has been verified against real data.

Paired with `schedule.0003_move_scheduletype_to_core`, which removes the model from the
schedule app's state. That migration depends on this one, so the order is deterministic.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="ChurchService",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("name", models.CharField(max_length=100)),
                        ("weekday", models.PositiveSmallIntegerField()),
                        ("time", models.TimeField()),
                    ],
                    options={"db_table": "schedule_scheduletype"},
                ),
            ],
        ),
    ]
