# Implementation Plan: Unified Church Service Catalogue

**Branch**: `007-unify-service-catalogue` | **Date**: 2026-08-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-unify-service-catalogue/spec.md`

## Summary

Collapse two models describing the same four church services into one catalogue owned by `core/`,
which becomes a Django app for the first time. `schedule.ScheduleType` keeps its rows and its ids and
becomes `core.ChurchService`; `songs.ServiceWindow` is deleted.

The move is done with `SeparateDatabaseAndState`, so **not a single row moves** — the 91 rota rows,
their ids, and the ids the Android app caches all stay exactly where they are. Real DDL is confined
to separate, clearly-labelled migrations afterwards.

Two things reading production changed. First, the catalogues are not the same set: Escola Bíblica
Dominical exists only on the hymnal side and takes no member rota, so the model needs `takes_rota`
separate from `active`. Second — and this reorders the whole plan — **`MonthlySchedule.schedule_type`
cascades on delete**, and feature 006 exposed a `DELETE` endpoint for service windows. Unifying
without fixing that would put 91 rota rows one admin click from destruction.

## Technical Context

**Language/Version**: Python 3.14 (pyenv), `.venv_windows`

**Primary Dependencies**: Django 6.0.3, DRF, dependency-injector, Pydantic. No new dependency.

**Storage**: PostgreSQL. One table renamed, three columns added, one column renamed, one row
inserted, one empty table dropped. **Zero rows moved or rewritten.**

**Testing**: pytest + DRF `APIClient`, mypy strict, ruff. Plus a manual before/after diff against a
restored production dump — the automated suite cannot prove data preservation.

**Target Platform**: Linux server behind nginx (`/ipbcb/`)

**Project Type**: Web service (REST API), single Android client

**Performance Goals**: N/A — the catalogue holds four rows.

**Constraints**: rota row ids MUST NOT renumber; rota API shapes MUST NOT change; the migration MUST
be verified against real data and MUST be reversible.

**Scale/Scope**: 3 apps touched, 5 migrations, ~20 files. Production today: 4 services, 91 rota rows,
24 member configs, 18 members, 0 hymn view events.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — see bottom.*

| Rule | Status | Notes |
|------|--------|-------|
| Features never import from each other | **PASS — this is the point** | Both features depend on `core`; neither on the other |
| Views never access repositories | PASS | No view layer change beyond what the repositories return |
| Services never import HTTP objects | PASS | Unchanged |
| Repositories are the only ORM layer | PASS | `DjangoScheduleRepository` and `DjangoHymnalHistoryRepository` keep sole ORM access |
| Models are pure entities | PASS | `ChurchService` has no service or repository import |
| DTOs via Pydantic | PASS | `ScheduleTypeDTO` gains `end_time`; `ServiceWindowDTO` retargets |
| DI via dependency-injector | PASS | No new service; existing registrations unchanged |
| Domain errors from `core/domain/exceptions.py` | PASS | New `ServiceInUseError(ConflictError)` for the protected delete |
| All user input via serializer | PASS | `weekday` range and `end_time > start_time` validated as before |
| No `.raw()` / formatted SQL | PASS | Migrations use Django operations; verification queries are read-only psql |
| No queries inside loops | PASS | No query pattern changes |
| Explicit permissions on every view | PASS | Unchanged |
| Models have `__str__`, `Meta.ordering`, `Meta.verbose_name` | PASS | `ChurchService` has all three |
| Type hints on public signatures | PASS | mypy strict must stay clean |
| All code in English | PASS | Service names are user-facing data, not code |
| **Migrations generated, not hand-written (§5)** | **VIOLATION — exception granted** | See Complexity Tracking |
| Never edit a migration applied in production | PASS | Every migration here is new |
| Data migrations document their reason | PASS | The backfill carries its reason at the top |

## Project Structure

### Documentation (this feature)

```text
specs/007-unify-service-catalogue/
├── plan.md                  # This file
├── spec.md                  # Feature specification
├── research.md              # Phase 0 — 11 decisions, R-01 is the urgent one
├── data-model.md            # Phase 1 — ChurchService, repointing, what must be identical
├── quickstart.md            # Phase 1 — the acceptance gate: capture, migrate, diff
├── contracts/               # Phase 1
│   ├── unchanged-rota-endpoints.md      # frozen shapes, pinned for verification
│   └── service-catalogue-endpoints.md   # the CRUD, now protected
├── checklists/
│   └── requirements.md
└── tasks.md                 # Phase 2 (/speckit-tasks — NOT created here)

specs/schedule/
└── spec.md                  # PREREQUISITE — does not exist yet (FR-019)
```

### Source Code (repository root)

```text
server/
├── config/
│   └── settings/base.py                 # Update: add "core" to INSTALLED_APPS
├── core/
│   ├── apps.py                          # New: AppConfig
│   ├── migrations/
│   │   ├── 0001_initial.py              # New: state-only CreateModel (hand-written)
│   │   ├── 0002_rename_and_extend.py    # New: table rename, field rename, new fields
│   │   └── 0003_backfill_catalogue.py   # New: data migration, reason documented
│   ├── models/
│   │   ├── __init__.py                  # New: re-export
│   │   └── church_service.py            # New: the single catalogue
│   ├── domain/
│   │   ├── weekday.py                   # New: the only weekday conversion
│   │   └── exceptions.py                # Update: ServiceInUseError
│   └── tests/unit/test_weekday.py       # New
└── features/
    ├── schedule/
    │   ├── models/schedule.py           # Update: repoint FKs, CASCADE -> PROTECT
    │   ├── migrations/0002_*.py         # New: state-only DeleteModel + AlterField
    │   ├── services/schedule_service.py # Update: drop WEEKDAYS_MAP, honour takes_rota
    │   ├── repositories/*.py            # Update: DTO gains end_time
    │   ├── dtos.py                      # Update: ScheduleTypeDTO
    │   └── admin.py                     # Update: unregister ScheduleType
    └── songs/
        ├── models/hymnal_history.py     # Update: delete ServiceWindow
        ├── migrations/0007_*.py         # New: DeleteModel
        ├── repositories/*.py            # Update: query core.ChurchService
        ├── services/hymnal_history_occurrences.py  # Update: convert weekday
        ├── services/hymnal_history_config_service.py # Update: protected delete
        ├── serializers/*.py             # Update: weekday range 1-7, takes_rota
        ├── views/hymnal_history.py      # Update: 409 on in-use delete
        └── admin.py                     # Update: unregister ServiceWindow
```

**Structure Decision**: `core` gains `apps.py`, `migrations/` and `models/`, mirroring the layout
every feature already uses. `core/domain/` stays framework-free and holds the weekday helper.
Everything else is an edit to existing files.

## Implementation Order

**Step 1 ships on its own and should ship first**, before any unification work.

1. **Close the data-loss path** — `MonthlySchedule.schedule_type` and
   `MemberScheduleConfig.schedule_type` from `CASCADE` to `PROTECT`, plus the regression test that
   deleting a referenced service fails. Independently valuable, independently shippable, and it
   removes the worst thing that could go wrong later (research R-01).

2. **Document the rota domain** — `specs/schedule/spec.md` for current behaviour. Required by §6.5
   before `schedule` code changes (FR-019), and the cheapest way to be certain the migration changes
   no behaviour: it forces reading every line that will be touched.

3. **One weekday convention** — `core/domain/weekday.py` with unit tests covering all seven days in
   both directions, *before* anything consumes it.

4. **`core` becomes an app** — `apps.py`, `INSTALLED_APPS`, empty `migrations/`. Verify the suite is
   still green with an installed-but-empty app.

5. **The move** — migrations 1 and 2 from research R-02: state-only, no DDL. Verify against the dump
   that nothing changed at all, then that the rota still works.

6. **Extend the model** — migrations 3 and 4: rename the table, rename `time` → `start_time`, add
   `end_time` / `active` / `takes_rota`, backfill, insert Escola Bíblica Dominical.

7. **Repoint the rota** — `WEEKDAYS_MAP` deleted in favour of the shared helper, `takes_rota`
   honoured in generation, DTO gains `end_time`.

8. **Repoint the hymnal** — repository queries `core.ChurchService`, `match_window` converts the
   weekday, serializers accept 1–7 and `takes_rota`, delete becomes protected.

9. **Delete `ServiceWindow`** — migration 5, model, admin, DTO, dead constants.

10. **Write the constitution changes** — the `core`-may-hold-models boundary (FR-016) and the §5
    exception with its reason (FR-017). Not paperwork: without the boundary, `core` becomes a
    dumping ground, and without the recorded exception the next reader assumes an oversight.

11. **Acceptance gate** — [quickstart.md](quickstart.md) end to end against a restored dump,
    including the rollback, plus the full suite, mypy and ruff.

Steps 5 and 6 are deliberately separate. If the state move and the DDL were one migration, a failure
would leave a half-migrated database with no clean revert point.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|-----------|------------|--------------------------------------|
| **Hand-written schema migrations (§5)** — exception granted by the user | A cross-app model move cannot be generated. `makemigrations` emits `DeleteModel` + `CreateModel`, which drops the table and destroys 91 rota rows. `SeparateDatabaseAndState` must be hand-authored. Separately, a non-interactive `makemigrations` turns `time` → `start_time` into `RemoveField` + `AddField`, silently discarding every stored time (research R-03) | Letting the generator do it destroys production data. The compensating control is FR-006: verified against a restored dump, with a tested rollback, before it goes near production |
| **`core` becomes an installed app holding models** | The constitution's own escape hatch — "use `core/` or signals" — has no other reading once two features need the same entity | A shared *feature* would still require a cross-feature import. Bounded by the new constitution rule: only entities used by two or more features |
| **FK field names stay `schedule_type` while pointing at `ChurchService`** | Those names are the wire format (`schedule_type_id`) the Android app sends and receives. FR-004 forbids changing it | Renaming the fields means renaming columns, DTOs and payloads — three risks for a cosmetic gain. Each declaration carries a comment |
| **`CASCADE` → `PROTECT` is in scope** although pre-existing | This feature is what makes the hazard reachable from an endpoint. Shipping the unification without it would put rota history one click from deletion | Deferring it leaves a live window where a routine admin action destroys data irreversibly |

## Post-Design Constitution Re-Check

Re-evaluated after `data-model.md` and `contracts/` were written:

- **The cross-feature import rule is now satisfied structurally**, not by convention. `songs` and
  `schedule` both depend on `core`; neither can reach the other. This was the reason for the feature
  and it holds in the design.
- **One new domain exception**: `ServiceInUseError(ConflictError)` → `409`, carrying the service id
  and the count of referencing rota entries, per the project's `extra_context()` pattern.
- **No new violations introduced.** The §5 exception is the only one, it was granted explicitly, and
  it is recorded in the constitution as part of step 10.
- **One deliberate behaviour change beyond the refactor**: services on any weekday now generate a
  rota (research R-05). It is User Story 4, it affects no current service, and it removes a silent
  failure rather than adding behaviour.
- **One field changes meaning**: `weekday` on the hymnal's service-window endpoints flips from
  `0 = Monday` to `1 = Sunday`. Safe only because that endpoint has never been deployed — and
  dangerous to reason about, because the value ranges overlap. Flagged prominently in the contract.
