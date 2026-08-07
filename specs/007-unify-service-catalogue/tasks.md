---

description: "Task list for Unified Church Service Catalogue"
---

# Tasks: Unified Church Service Catalogue

**Input**: Design documents from `specs/007-unify-service-catalogue/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: included and not optional — CLAUDE.md §10 requires a test for every new function and a
regression test for every bug fix. Two tasks here fix real bugs (T003, T041).

**Organization**: grouped by user story. Read the dependency note before assuming they are
independent — on this feature, two of them are not.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different file, no dependency on an incomplete task
- **[Story]**: US1…US4
- Every task names its exact file path

## Before you start

**This feature edits production data structures.** Two rules apply to every task below:

1. Work against a **restored production dump**, and keep a second copy outside the repository. You
   will restore more than once.
2. **Never let `makemigrations` write a migration for the model move or the field rename.** It emits
   `DeleteModel` + `CreateModel` (drops 91 rota rows) and `RemoveField` + `AddField` (discards the
   three stored times). Both are silent. See research [R-02](research.md) and [R-03](research.md).

Commits must each leave the tree type-consistent — the mypy hook checks the whole tree and
`pre-commit` stashes unstaged changes, so a half-staged interdependent change fails misleadingly.

---

## Phase 1: Setup — close the data-loss path first

**Purpose**: one small, independently shippable fix that must land before anything else

**⚠️ Ship T001–T003 on their own.** Today, deleting a service cascades and deletes every rota row
that referenced it. Feature 006 already exposed a `DELETE` endpoint that will reach this path the
moment the catalogue is unified. This is 91 rota rows, growing monthly, one click from gone.

- [X] T001 Change `on_delete` from `CASCADE` to `PROTECT` on `MonthlySchedule.schedule_type` and `MemberScheduleConfig.schedule_type` in `server/features/schedule/models/schedule.py`, with a comment on each explaining that rota rows are a record of what happened (research R-01)
- [X] T002 Generate the migration with `python manage.py makemigrations schedule` — this one **is** safe to generate, it is a plain `AlterField`. Verify it contains only the two `AlterField` operations and no table changes
- [X] T003 Add a regression test in `server/features/schedule/tests/unit/test_models.py`: deleting a `ScheduleType` that has rota rows raises `ProtectedError` and leaves every row intact; the same for one with member configurations
- [X] T004 Write `specs/schedule/spec.md` documenting the rota domain **as it exists today** (CLAUDE.md §6.5, FR-019): weighted member selection via `weight` expansion and shuffle, the least-used tie-break, the global per-month usage count, pinned assignments keyed by `(schedule_type_id, date)`, the 30-minute overwrite window and `ScheduleOverwriteError`, `replace_schedules` deleting and recreating the whole month in a transaction, and the three endpoints with their exact payloads including the tolerant parsing in `_parse_schedule_save_payload`. Nothing may change in `schedule/` until this exists

**Checkpoint**: the data-loss path is closed and the rota domain is documented. Deployable as-is.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the shared pieces every story needs

**⚠️ CRITICAL**: no user story work can begin until this phase is complete

- [X] T005 [P] Create `server/core/domain/weekday.py` with `to_python_weekday(stored: int) -> int` returning `(stored + 5) % 7` and `from_python_weekday(python_weekday: int) -> int` returning `(python_weekday + 1) % 7 + 1`, documenting that stored is `1 = Sunday … 7 = Saturday` and Python's is `0 = Monday … 6 = Sunday` (research R-04)
- [X] T006 [P] Add unit tests in `server/core/tests/unit/test_weekday.py` covering **all seven days in both directions** and asserting the round trip is identity. Pin the three real values explicitly: Sunday `1 ↔ 6`, Tuesday `3 ↔ 1`, Thursday `5 ↔ 3`
- [X] T007 [P] Add `ServiceInUseError(ConflictError)` to `server/core/domain/exceptions.py`, carrying `service_id`, `service_name` and `rota_entries`, with `extra_context()` following the existing pattern and a message naming the service and the count
- [X] T008 Make `core` a Django app: create `server/core/apps.py` with an `AppConfig`, create `server/core/migrations/__init__.py`, and add `"core"` to `INSTALLED_APPS` in `server/config/settings/base.py` before the feature apps (research R-06)
- [X] T009 Run the full suite with `core` installed but empty and confirm it is still green. An installed app with no models must change nothing

**Checkpoint**: one weekday function exists and is tested; `core` is an app. Stories can begin.

---

## Phase 3: User Story 1 — Nothing breaks (Priority: P1) 🎯 MVP

**Goal**: `ScheduleType` becomes `core.ChurchService` without a single row moving.

**Independent Test**: capture every rota row, member config and service id before; migrate; capture
again; the diff must be empty.

**Contract**: [contracts/unchanged-rota-endpoints.md](contracts/unchanged-rota-endpoints.md)

### Verification harness first

- [X] T010 [US1] Capture the baseline from the restored dump per [quickstart.md](quickstart.md) step 0 — rota rows, member configs, service rows, and the `/api/schedule/current/` response — into files you will diff against. Confirm the expected shape: 3 services (ids 1, 2, 3), 91 rota rows, 24 member configs

### The move — state only, zero DDL

- [X] T011 [US1] Create `server/core/models/church_service.py` with `ChurchService` declaring **exactly the fields that exist in the table today** — `name`, `weekday`, `time` — and `db_table = "schedule_scheduletype"`. Do not add the new fields yet; the state must match the real table at this point or every later operation is computed against a lie (research R-02)
- [X] T012 [P] [US1] Create `server/core/models/__init__.py` re-exporting `ChurchService` in the `X as X` style the features use
- [X] T013 [US1] **Hand-write** `server/core/migrations/0001_initial.py`: a single `SeparateDatabaseAndState` with `state_operations=[CreateModel(...)]` and **no** database operations. Document at the top why it is hand-written and that it must not touch the database
- [X] T014 [US1] Repoint the foreign keys in `server/features/schedule/models/schedule.py` to `core.ChurchService`, **keeping the field names `schedule_type`** on both models, with a comment explaining that the names are the wire format the Android app sends and receives (research R-07). Delete the local `ScheduleType` class
- [X] T015 [US1] **Hand-write** `server/features/schedule/migrations/0003_move_scheduletype_to_core.py`: `SeparateDatabaseAndState` with `state_operations=[DeleteModel("ScheduleType")]` plus state-only `AlterField` on both foreign keys, depending on `core.0001`. No database operations
- [X] T016 [P] [US1] Move the admin registration: unregister `ScheduleType` in `server/features/schedule/admin.py` and register `ChurchService` in a new `server/core/admin.py`
- [X] T017 [US1] Update `server/features/schedule/repositories/schedule_repository.py` and `server/features/schedule/dtos.py` to import from `core.models` instead of `features.schedule.models.schedule`. `ScheduleTypeDTO` keeps its shape for now

### Prove nothing moved

- [X] T018 [US1] Restore the dump, run `python manage.py migrate`, and diff the captures from T010. **Any difference fails this story.** Confirm service ids are still 1, 2, 3 and the rota count is still 91
- [X] T019 [US1] Add an integration test in `server/features/schedule/tests/integration/test_schedule_views.py` asserting `/api/schedule/current/` still groups by service name and still returns the same `schedule_type.id` values, and that save accepts both the flat and nested payload forms

**Checkpoint**: the model lives in `core`, nothing changed on disk, the rota works. **This is the MVP** — the risky half is done and verified before any new behaviour is added.

---

## Phase 4: User Story 2 — One place to change a service time (Priority: P2)

**Goal**: one catalogue with the fields both features need; the duplicate is gone.

**Independent Test**: change a service's start time once, then confirm both the rota and the hymn
occurrence grouping use the new time.

**Contract**: [contracts/service-catalogue-endpoints.md](contracts/service-catalogue-endpoints.md)

### Extend the model

- [X] T020 [US2] Extend `ChurchService` in `server/core/models/church_service.py`: rename `time` to `start_time`, add `end_time`, `active` (default `True`) and `takes_rota` (default `True`), set `db_table = "core_churchservice"`, add `Meta.ordering`, `verbose_name`, `__str__`, and both check constraints from [data-model.md](data-model.md)
- [X] T021 [US2] **Hand-write** `server/core/migrations/0002_rename_and_extend.py`: `AlterModelTable` to `core_churchservice`, `RenameField` `time` → `start_time`, then `AddField` for `end_time` (nullable for now), `active` and `takes_rota`. **`RenameField` must be written by hand** — a non-interactive `makemigrations` emits remove-plus-add and silently discards all three stored times (research R-03)
- [X] T022 [US2] **Hand-write** `server/core/migrations/0003_backfill_catalogue.py` with its reason at the top: set `end_time` to 20:30 for Terça and Quinta and 21:00 for Domingo Liturgia de Adoração, set `takes_rota=True` on all three, insert Escola Bíblica Dominical (weekday 1, 09:00–10:00, `takes_rota=False`) with `get_or_create` by name, then `AlterField` making `end_time` non-null. The reverse removes the EBD row and nulls the added columns
- [X] T023 [US2] Add tests in `server/core/tests/unit/test_church_service.py` for `__str__`, the `end_time > start_time` constraint, the `weekday` 1–7 constraint, and that `active` and `takes_rota` are independent

### Repoint the rota

- [X] T024 [US2] Add `end_time`, `active` and `takes_rota` to `ScheduleTypeDTO` in `server/features/schedule/dtos.py` and populate them in `DjangoScheduleRepository.list_schedule_types`
- [X] T025 [US2] Filter rota generation to services where `takes_rota` is true, in `server/features/schedule/services/schedule_service.py`. Escola Bíblica Dominical must never produce a rota row (FR-020, SC-009)

### Repoint the hymnal

- [X] T026 [US2] Change `DjangoHymnalHistoryRepository` in `server/features/songs/repositories/hymnal_history_repository.py` to query `core.ChurchService` — `list_active_service_windows` filters `active=True`, and the CRUD methods operate on the shared catalogue
- [X] T027 [US2] Update `server/features/songs/repositories/interfaces.py` and `server/features/songs/hymnal_history_dtos.py`: the protocol signatures take `ChurchService`, and `ServiceWindowDTO` gains `takes_rota`
- [X] T028 [US2] Update `server/features/songs/serializers/hymnal_history_serializers.py`: `weekday` range becomes 1–7 with an error message spelling out `1 = Sunday`, and add the `takes_rota` field. Remove the `MIN_WEEKDAY` / `MAX_WEEKDAY` import from the deleted model
- [X] T029 [US2] Make delete protected in `server/features/songs/services/hymnal_history_config_service.py`: raise `ServiceInUseError` when the service has rota rows or member configurations, so the endpoint returns `409` naming the service and the count instead of destroying history
- [X] T030 [US2] Update `server/features/songs/views/hymnal_history.py` for the `takes_rota` field and confirm `ServiceInUseError` maps to `409` through the existing exception handler

### Delete the duplicate

- [X] T031 [US2] Remove `ServiceWindow` from `server/features/songs/models/hymnal_history.py` along with `MIN_WEEKDAY` and `MAX_WEEKDAY`, and drop it from `server/features/songs/models/__init__.py` and `server/features/songs/admin.py`
- [X] T032 [US2] Generate `server/features/songs/migrations/0007_delete_servicewindow.py` with `makemigrations songs` — a plain `DeleteModel` is safe to generate. Verify it drops only that table
- [X] T033 [US2] Update the integration tests in `server/features/songs/tests/integration/test_hymnal_history_admin_api.py` and `test_hymnal_history_seed.py` for the new weekday convention, the `takes_rota` field, and the protected delete returning `409`
- [X] T034 [US2] Add a test proving one edit reaches both features: change a service's `start_time`, then assert the rota generator and `collapse_events` both use the new value
- [X] T035 [US2] Update `specs/songs/spec.md` — `ServiceWindow` is gone, the catalogue is shared, the weekday convention flipped, and the seed migration description changes (CLAUDE.md §6.2)

**Checkpoint**: one catalogue, one edit, no duplicate. The feature's value is delivered.

---

## Phase 5: User Story 3 — One weekday convention (Priority: P2)

**Goal**: a search for weekday arithmetic finds exactly the two functions in `core/domain/weekday.py`.

**Independent Test**: assert the same stored value resolves to the same real weekday in the rota
generator and in hymn occurrence grouping.

**⚠️ Not optional after US2.** The stored convention flips the moment the hymnal reads the shared
catalogue, so T037 must land with Phase 4 or the hymnal silently stops matching windows.

- [X] T036 [US3] Delete `WEEKDAYS_MAP` from `server/features/schedule/services/schedule_service.py` and use `to_python_weekday` from `core/domain/weekday.py` in `_month_dates_for_weekday`
- [X] T037 [US3] Convert the weekday in `match_window` in `server/features/songs/services/hymnal_history_occurrences.py` — it currently compares `moment.weekday()` directly against the stored value, which is wrong under the new convention. Use `from_python_weekday` so the comparison happens in stored terms
- [X] T038 [US3] Update `server/features/songs/tests/unit/test_hymnal_history_occurrences.py` for the new convention: Sunday becomes `1`, not `6`. Every fixture weekday changes
- [X] T039 [US3] Add a cross-feature test in `server/core/tests/unit/test_weekday.py` asserting that a service stored on weekday `1` produces Sunday dates in the rota generator **and** matches hymn views recorded on a Sunday
- [X] T040 [US3] Verify no second convention survives. **The grep as originally written was wrong** — it does not come back empty, and should not. `WEEKDAYS_MAP` is gone from the code (only a comment and a test docstring name it, both explaining why it was removed). `calendar.SUNDAY` survives in `test_monthly_scheduler_helpers.py`, which tests `_month_dates_for_weekday` — a function that legitimately takes a **Python** weekday, where `calendar.SUNDAY == 6` is the correct convention used at the boundary. What SC-005 actually requires is one *stored* convention with a single conversion point, and that holds: every stored-to-Python translation goes through `core/domain/weekday.py`

**Checkpoint**: one convention, verified from both sides.

---

## Phase 6: User Story 4 — Services on any weekday work (Priority: P3)

**Goal**: a service on any of the seven weekdays generates a rota; nothing is skipped in silence.

**Independent Test**: add a Saturday service with `takes_rota` true, generate a rota, confirm rows
appear, delete it.

**Mostly free once T036 lands** — the silent skip disappears with the map it depended on.

- [X] T041 [US4] Confirm the `if schedule_type.weekday not in WEEKDAYS_MAP: continue` guard is gone from `server/features/schedule/services/schedule_service.py` and that the only remaining skip is the intentional `takes_rota` filter. Any service that still cannot be scheduled must surface a reason, never a silent omission
- [X] T042 [US4] Add a regression test in `server/features/schedule/tests/integration/test_monthly_scheduler.py` generating a month for a service on Saturday (weekday `7`) and asserting rows are produced — this fails before T036 and passes after
- [X] T043 [US4] Add the same for Monday, Wednesday and Friday, the other weekdays the old map silently dropped

**Checkpoint**: all four stories complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T044 Record the shared-layer boundary in `specs/constitution.md` (FR-016): `core/` may contain models, but only entities genuinely shared by two or more features — if exactly one feature uses it, it belongs to that feature. Without the boundary `core` becomes a dumping ground
- [X] T045 Record the §5 exception in `specs/constitution.md` (FR-017) with its reason: a cross-app model move cannot be generated without destroying data, and the compensating control is verification against a restored production dump plus a tested rollback
- [X] T046 Run `mypy .` from `server/` and resolve every error
- [X] T047 Run `ruff check server/` and `ruff format server/` from the repository root
- [X] T048 Run the full suite: `pytest` from `server/`. Every existing test must pass, especially `features/schedule/tests/`, which exercises the generator whose weekday handling changed
- [X] T049 Walk [quickstart.md](quickstart.md) steps 0–7 against the restored dump. Steps 0–4 and 6–7 ran as written. Step 5 (the protected delete) was verified two ways: an integration test in `server/core/tests/integration/test_service_deletion_api.py` asserting `409`, and directly against the production copy, where deleting the Sunday service was refused with **39 rota entries** named in the message and all 91 rows intact
- [X] T050 **Test the rollback** ([quickstart.md](quickstart.md) step 8): restore, migrate forward, migrate back, confirm 91 rota rows and the restored table name. A reverse migration that has never been run is not a rollback plan (FR-005, SC-008)
- [X] T051 Re-read `specs/schedule/spec.md` from T004 against the changed code and update anything the unification altered — spec and code go together (CLAUDE.md §6.2)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T001–T003 are independently shippable and should ship first
- **Foundational (Phase 2)**: T004 must precede any `schedule/` change. Blocks all stories
- **US1 (Phase 3)**: depends on Phase 2. **Ship and verify before starting Phase 4**
- **US2 (Phase 4)**: depends on US1
- **US3 (Phase 5)**: T036 depends on T005; **T037 must land with Phase 4**, see below
- **US4 (Phase 6)**: depends on T036
- **Polish (Phase 7)**: depends on everything

### Honest note on story independence

The skill's usual assumption — that stories ship independently — **does not hold here**, and
pretending otherwise would produce a broken intermediate state:

- **US1 is a genuine checkpoint.** The model lives in `core`, nothing has changed on disk, and the
  rota works. Stop here safely.
- **US2 and US3 are one change.** The stored weekday convention flips the moment the hymnal reads
  the shared catalogue. Shipping US2 without T037 leaves `match_window` comparing a `1 = Sunday`
  value against Python's `0 = Monday` — every window silently stops matching, and the dashboard
  quietly falls back to day-collapsing with no error.
- **US4 is genuinely optional** and can be dropped without affecting anything else.

### Within Each Story

- Verification harness before the change it verifies (T010 before T018)
- Model state before migrations; state-only migrations before DDL
- Migrations before the code that depends on the new fields
- Tests updated in the same commit as the behaviour they cover

### Parallel Opportunities

- Phase 1: T001–T002 are one change; T003 and T004 are independent of each other
- Phase 2: T005, T006, T007 are three different files — parallel. T008 touches settings, so it is not
- Phase 3: T012 and T016 are parallel; everything else is sequential by design
- Phase 4: the rota side (T024–T025) and the hymnal side (T026–T030) are different features and can
  be worked in parallel after T022
- Across stories: **do not parallelise US1 with US2.** US1's whole purpose is to prove nothing moved,
  and that proof is worthless if other changes are in flight

---

## Parallel Example: Phase 2 Foundational

```bash
# Three independent files:
Task: "T005 Weekday conversion in server/core/domain/weekday.py"
Task: "T006 Weekday tests in server/core/tests/unit/test_weekday.py"
Task: "T007 ServiceInUseError in server/core/domain/exceptions.py"
```

## Parallel Example: Phase 4, after the migrations land

```bash
# Rota side and hymnal side touch different features:
Task: "T024 ScheduleTypeDTO gains end_time in server/features/schedule/dtos.py"
Task: "T026 Repository queries core.ChurchService in .../hymnal_history_repository.py"
```

---

## Implementation Strategy

### Ship Phase 1 immediately, on its own

T001–T003 close a live path where one admin click destroys 91 rota rows. It has nothing to do with
the unification and should not wait for it.

### MVP = through User Story 1

1. Phase 1 → deploy (the `PROTECT` fix)
2. Phase 2 → foundation
3. Phase 3 → **stop and verify against the dump**

At that point the model lives in `core`, the rota is provably untouched, and the risky half is
behind you. That is the right place to pause, because everything after it is additive.

### Then the value

4. Phase 4 + T037 together → the catalogue is unified and there is one place to edit a service
5. Phase 5 → the second convention is gone
6. Phase 6 → any weekday works
7. Phase 7 → constitution, rollback test, full gate

### The acceptance gate

The feature is not done when the tests pass. It is done when **T018, T049 and T050** have all been
run against a restored production dump: nothing moved, everything works, and the rollback has
actually been executed rather than assumed.

---

## Notes

- `[P]` = different file, no dependency on an incomplete task
- Commit spec and code together (CLAUDE.md §6.2), and keep each commit type-consistent
- **The two migrations that must never be generated**: the model move (T013, T015) and the field
  rename (T021). Both have silent, destructive auto-generated forms
- Service ids 1, 2, 3 are load-bearing — the Android app caches them. Nothing may renumber
