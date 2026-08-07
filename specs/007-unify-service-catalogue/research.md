# Phase 0 Research: Unified Church Service Catalogue

Decisions taken before design, with the alternatives rejected. Every NEEDS CLARIFICATION from
Technical Context is resolved — the production backup restored on 2026-08-07 answered the only open
question.

---

## R-01: ⚠️ `CASCADE` on the rota foreign key — a data-loss path this feature would open

**Finding**: `features/schedule/models/schedule.py:34` declares

```python
schedule_type = models.ForeignKey(ScheduleType, on_delete=models.CASCADE)
```

Deleting a service **deletes every rota row that ever referenced it**. Today that is only reachable
from the Django admin, by someone deliberately deleting a service.

Feature 006 added `DELETE /api/hymnal-history/service-windows/{id}/`. The moment that endpoint points
at the unified catalogue, **an admin deleting what looks like a hymnal display setting silently
destroys the rota history** — 91 rows today, growing every month. No warning, no error, no undo.

**Decision**: change both rota foreign keys to `PROTECT` **before** the catalogue is unified, and
treat that as the first task of the feature rather than a detail of it.

- `MonthlySchedule.schedule_type` → `PROTECT` — rota history is a record of what happened.
- `MemberScheduleConfig.schedule_type` → `CASCADE` is arguably right (a configuration for a service
  that no longer exists is meaningless) but is changed to `PROTECT` too, so deletion fails loudly
  and an admin deactivates instead. FR-011 already provides deactivation as the intended path.

**Rationale**: this is the difference between "a migration that must not go wrong" and "a system
where a routine admin click can go wrong forever". It is a pre-existing hazard, but this feature is
what makes it reachable, so it belongs here.

**Cost**: `on_delete` is enforced by Django, not by the database, so this is a state-level field
change with no DDL. It is nearly free.

**Alternatives rejected**:
- *Leave `CASCADE` and remove the DELETE endpoint* — hides the hazard rather than fixing it, and the
  admin site still exposes it.
- *Fix it in a later feature* — leaves a window where the unified catalogue is live and one click
  from destroying rota history.

---

## R-02: Moving a model between apps without touching a single row

**Decision**: `SeparateDatabaseAndState` for the ownership move, with all real DDL kept in separate,
clearly-labelled migrations afterwards.

Django models are tied to an app. `makemigrations` sees a move as `DeleteModel` + `CreateModel` —
which drops `schedule_scheduletype` and takes 91 rota rows with it. `SeparateDatabaseAndState` lets
the *state* change while the database does nothing at all.

**Sequence** (five migrations across three apps):

| # | App | Operation | Touches data? |
|---|-----|-----------|---------------|
| 1 | `core` `0001_initial` | `SeparateDatabaseAndState(state_operations=[CreateModel(ChurchService, db_table="schedule_scheduletype")])` — fields exactly as they exist today: `name`, `weekday`, `time` | **No** — state only |
| 2 | `schedule` `0002` | `SeparateDatabaseAndState(state_operations=[DeleteModel(ScheduleType)])` + `AlterField` on both FKs to target `core.ChurchService` | **No** — state only; the column and constraint are already correct |
| 3 | `core` `0002` | `AlterModelTable` → `core_churchservice`; `RenameField` `time` → `start_time`; `AddField` `end_time` (nullable), `active`, `takes_rota` | Yes — DDL, but no row content changes |
| 4 | `core` `0003` | Data migration: backfill `end_time`, set `takes_rota`, insert Escola Bíblica Dominical; then `AlterField` making `end_time` non-null | Yes — writes |
| 5 | `songs` `0007` | `DeleteModel(ServiceWindow)` | Drops an empty table |

Migration 2 must declare a dependency on migration 1 so ordering is deterministic.

**Why the state move comes first and DDL second**: if migration 1 declared the *final* field set, its
state would not match the real table and every later operation would be computed against a lie.
Creating the state as-is and then evolving it keeps Django's picture and the database in step at
every point, which is also what makes the sequence reversible.

**`AlterModelTable` is safe**: PostgreSQL's `ALTER TABLE ... RENAME` preserves rows, primary keys,
indexes and every foreign key constraint pointing at the table, and Django wraps migrations in a
transaction on PostgreSQL. Nothing renumbers.

**Alternatives rejected**:
- *Create a new table, copy rows, repoint foreign keys, drop the old one* — the obvious approach and
  the wrong one. New rows get new ids, which violates FR-002 and would make the Android app save
  rotas against the wrong services using ids it cached.
- *Keep `db_table = "schedule_scheduletype"` forever* — zero DDL, maximum safety. Rejected because a
  `schedule_`-prefixed table owned by `core` is a permanent wart that will confuse the next reader,
  and the rename is genuinely safe. Recorded as the fallback if the rename misbehaves on the dump.

---

## R-03: `RenameField` cannot be auto-generated here

**Decision**: hand-write the `RenameField` for `time` → `start_time`.

`makemigrations` detects renames by *asking* — "Did you rename scheduletype.time to
scheduletype.start_time? [y/N]". Non-interactively it does not ask; it emits `RemoveField` +
`AddField`, which **silently discards every stored time**. Three services would come back with a
null start time and rota generation would break.

This is a second, independent reason the §5 exception is needed, and a specific thing to check when
reviewing the generated output rather than trusting it.

---

## R-04: One weekday convention, one conversion function

**Decision**: keep `1 = Sunday … 7 = Saturday`, confirmed from production. Put the conversion to and
from Python's `weekday()` in **one** module, `core/domain/weekday.py`, and delete every other
weekday translation in the codebase.

```
to_python_weekday(stored)  -> (stored + 5) % 7      # 1 (Sun) -> 6, 3 (Tue) -> 1, 7 (Sat) -> 5
from_python_weekday(py)    -> (py + 1) % 7 + 1      # 6 (Sun) -> 1, 1 (Tue) -> 3, 5 (Sat) -> 7
```

**Rationale**: the rota side carries live data; converting it risks breaking generation silently for
no functional gain. The hymn side has **zero rows**, so converting *it* is free — only the seeded
window rows change, and they are superseded anyway.

**Why this is the highest-value line in the feature**: "Terça de Oração" is stored as `weekday=3`
under one convention and `weekday=1` under the other, and **both numbers are legal in both
systems**. Nothing about the value reveals which it is. A single shared function means the question
can only be answered one way.

**Consumers to update**:
- `schedule_service.WEEKDAYS_MAP` — deleted, replaced by `to_python_weekday`. This alone fixes R-05.
- `hymnal_history_occurrences.match_window` — currently compares `moment.weekday()` directly against
  the stored value; must convert first.

---

## R-05: The silent-skip bug disappears for free

**Finding**: `schedule_service.py:15` maps only three weekdays:

```python
WEEKDAYS_MAP = {1: calendar.SUNDAY, 3: calendar.TUESDAY, 5: calendar.THURSDAY}
```

and line 94 does `if schedule_type.weekday not in WEEKDAYS_MAP: continue`. A service on any other
weekday generates **no rota rows, with no error**. It works today only because the church's three
services happen to fall on the three mapped days.

**Decision**: replace the map with `to_python_weekday` from R-04. Every weekday works, and the
`continue` disappears with the map. The explicit skip that remains is the intended one: services
where `takes_rota` is false.

This is User Story 4, and it costs nothing once R-04 is done.

---

## R-06: `core` becomes a Django app

**Decision**: add `core` to `INSTALLED_APPS`, with `core/apps.py`, `core/migrations/`, and models
under `core/models/` re-exported from `core/models/__init__.py` — the same layout every feature uses.

**Why `core/models/` and not `core/domain/`**: Django resolves models from `<app_label>.models`.
`core/domain/` holds framework-free domain code (exceptions, the weekday helper) and keeping ORM
models out of it preserves that distinction. `core/models/` mirrors `features/*/models/`, so the
layout is one a reader already knows.

**The boundary must be written into the constitution** (FR-016), because this is the change that
makes `core` capable of accumulating models:

> `core/` may contain models, but only entities genuinely shared by two or more features. If exactly
> one feature uses it, it belongs to that feature.

**Note**: `core` has never been an installed app — not even when it lived at `features/core/` before
commit `716609a`. There is no recorded rationale anywhere; it simply never needed one. Recorded here
so the next reader knows this was considered rather than overlooked.

---

## R-07: Foreign key **field names** stay as they are

**Decision**: `MemberScheduleConfig.schedule_type` and `MonthlySchedule.schedule_type` keep their
names. Only what they point at changes.

**Rationale**: FR-004 forbids any API change. Those field names surface directly as
`schedule_type_id` in the rota preview and save payloads, and as `schedule_type` in responses. The
Android app sends and receives them. Renaming the fields means renaming the database columns,
changing the DTOs, and changing the wire format — three risks bought for a cosmetic gain.

The resulting slight mismatch — a field called `schedule_type` pointing at `ChurchService` — is
deliberate and gets a comment at each declaration. Renaming it is a separate, API-versioned change
if it is ever worth doing.

---

## R-08: How `songs` stops depending on `ServiceWindow`

**Decision**: the hymnal's repository queries `core.ChurchService`; `ServiceWindow` is deleted along
with its model, migrations state, admin registration and DTO.

Nothing in the hymnal *stores* a reference to a window — `HymnalViewEvent` has no such foreign key,
because occurrences are derived at read time. That is what makes this side cheap: only the read path
changes.

Touch list (13 files reference `ServiceWindow` today): the model, `models/__init__.py`, `admin.py`,
`hymnal_history_dtos.py`, `repositories/interfaces.py`, `repositories/hymnal_history_repository.py`,
`serializers/hymnal_history_serializers.py`, `services/hymnal_history_config_service.py`,
`services/hymnal_history_occurrences.py`, `views/hymnal_history.py`, `urls.py`, and migrations
`0004`/`0006`.

**The service-window endpoints keep their paths** (FR-013) and now manage the shared catalogue. With
R-01 in place, `DELETE` on a service that has rota rows fails with a domain error instead of
destroying them.

---

## R-09: Verifying against real data is the acceptance gate

**Decision**: the migration is exercised against a restored production dump, and the check is a
**before/after diff of the full rota**, not a spot check.

```
1. restore dump  →  2. capture: every rota row, every service id, every member config
3. migrate       →  4. capture again  →  5. diff must be empty except the new columns
```

**Rationale**: FR-006 exists because the failure mode here is silent. A migration under the wrong
weekday assumption still runs, still generates rotas, and puts them on the wrong days. Only
comparing real output against real output catches that.

The dump is already restored locally (91 rota rows, 24 configs, 18 members, 3 services). The user
keeps backups outside the repository, and `*.sql*` is now git-ignored.

**Rollback**: every migration in the sequence is reversible, and the reverse order restores the
prior structure. This must be *tested*, not assumed — running the reverse against the dump is part
of the same gate.

---

## R-10: The `schedule` spec is a prerequisite, and it is real work

**Decision**: write `specs/schedule/spec.md` describing current behaviour **before** touching
`schedule` code, per CLAUDE.md §6.5. It blocks implementation, not planning.

What has to be documented, none of which is written down today:

- Weighted random member selection — `weight` expands a member into repeated entries, then shuffle
- The least-used tie-break, and the global per-month usage count across all services
- Pinned assignments (`fixed`), keyed by `(schedule_type_id, date)`
- The 30-minute overwrite window after the first save, enforced by `ScheduleOverwriteError`
- `replace_schedules` deleting and recreating the whole month inside a transaction
- The three endpoints and their exact payload shapes, including the tolerant parsing in
  `_parse_schedule_save_payload` that accepts both `schedule_type_id` and nested `schedule_type.id`

Writing this is also the cheapest way to be sure the migration does not change behaviour: it forces
reading every line that will be touched.

---

## R-11: Observability and safety rails during the migration

**Decision**: no new logging or metrics. The migrations are one-shot and verified offline; a
counter that fires once has no consumer.

**Not doing**: a maintenance-mode flag or downtime window. The whole sequence is a handful of
metadata operations plus one `ALTER TABLE RENAME`, all inside a transaction on PostgreSQL. The
church app has a single client and no meaningful concurrent write load at deploy time.
