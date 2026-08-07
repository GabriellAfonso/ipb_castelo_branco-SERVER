"""Rename the table and add the columns both features need.

The `RenameField` below is HAND-WRITTEN ON PURPOSE and must never be regenerated.
`makemigrations` only detects a rename by asking interactively; run non-interactively
it emits RemoveField + AddField instead, which SILENTLY DISCARDS every stored time.
All three services would come back with no start time and rota generation would break.
See specs/007-unify-service-catalogue/research.md R-03.

`AlterModelTable` is a real `ALTER TABLE ... RENAME` — PostgreSQL preserves rows,
primary keys, indexes and every foreign key constraint pointing at the table, and
Django wraps this in a transaction. Nothing renumbers.

`end_time` arrives nullable so existing rows survive; 0003 backfills it and makes it
required. The check constraints are added there too, once the data satisfies them.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        # The state hand-off must be complete before the table is renamed.
        ("schedule", "0003_move_scheduletype_to_core"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="churchservice",
            table="core_churchservice",
        ),
        migrations.RenameField(
            model_name="churchservice",
            old_name="time",
            new_name="start_time",
        ),
        migrations.AddField(
            model_name="churchservice",
            name="end_time",
            field=models.TimeField(null=True),
        ),
        migrations.AddField(
            model_name="churchservice",
            name="active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="churchservice",
            name="takes_rota",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterModelOptions(
            name="churchservice",
            options={
                "ordering": ["weekday", "start_time"],
                "verbose_name": "church service",
                "verbose_name_plural": "church services",
            },
        ),
    ]
