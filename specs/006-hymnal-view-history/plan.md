# Implementation Plan: Hymnal View History

**Branch**: `006-hymnal-view-history` | **Date**: 2026-08-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-hymnal-view-history/spec.md`

## Summary

Add passive hymnal usage telemetry to the existing `songs` feature: the Android app records which
hymns were opened and for how long, buffers them offline, and syncs batches to a public throttled
ingest endpoint. Admin endpoints then read that data as **occurrences** — a hymn sung once by the
congregation, collapsed by service window rather than counted per person.

Three new models (`HymnalViewEvent`, `ServiceWindow`, `HymnalHistorySettings`), seven endpoints, and
no change to any existing model, view or response. The two design pivots are: **idempotency via a
client-generated `client_event_id`**, which makes the sync retry-safe and removes the need for a
confirmation endpoint; and **occurrences derived at read time**, which lets an admin edit service
windows without ever rewriting stored history.

Phase 0 resolved every open technical question except the church's real service times
([research.md](research.md) R-11) — a data-migration input, not a blocker.

## Technical Context

**Language/Version**: Python 3.14 (pyenv)

**Primary Dependencies**: Django 5.x, Django REST Framework, dependency-injector, Pydantic,
drf-spectacular, SimpleJWT. No new third-party dependency.

**Storage**: PostgreSQL — three new tables, no change to existing schema

**Testing**: pytest + DRF `APIClient` (`DJANGO_SETTINGS_MODULE=config.settings.test`), mypy

**Target Platform**: Linux server behind nginx (`/ipbcb/` prefix)

**Project Type**: Web service (REST API), single Android client

**Performance Goals**: ingest of a 200-event batch in a constant 4 queries; a 366-day report served
from one range scan plus two small lookups. Church scale — tens of thousands of events per year.

**Constraints**: ingest endpoint is unauthenticated (throttled); reports bounded at 366 days;
all time reasoning in `America/Sao_Paulo`; existing `Played`/`Song` flow byte-identical.

**Scale/Scope**: ~19 new files, 3 models, 3 migrations, 7 endpoints, 3 services, 1 repository.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — see bottom.*

| Rule | Status | Notes |
|------|--------|-------|
| Features never import from each other | PASS | Lives in `songs` because `Hymn` does. `ServiceWindow` is owned here, not read from `schedule` (research R-01) |
| Views never access repositories | PASS | Views call `HymnalHistoryIngestService`, `HymnalHistoryReportService`, `HymnalHistoryConfigService` only |
| Services never import HTTP objects | PASS | Services take Pydantic DTOs and plain values; the JWT-derived `user_id` is passed in as an `int \| None` by the view |
| Repositories are the only ORM layer | PASS | `DjangoHymnalHistoryRepository` owns every query |
| Models are pure entities | PASS | No service/repository imports; the settings singleton is materialised by the repository, not a `Model.load()` (research R-06) |
| DTOs via Pydantic | PASS | 8 DTOs extending `StrictBaseModel` (`data-model.md`) |
| DI via dependency-injector | PASS | Repository, 3 services and the `Clock` registered in `config/di.py`; view module added to `wiring_config` |
| Domain errors from `core/domain/exceptions.py` | PASS | `NotFoundError` for a missing window; `ValidationError` for range/batch violations. New subclasses named with the offending value |
| All user input via serializer | PASS | DRF serializers at the boundary; per-event validation deliberately inside the service so one bad event cannot fail the batch (research R-09) |
| No `.raw()` / formatted SQL | PASS | ORM only. Deliberately avoids adding a second PostgreSQL-only query (research R-04) |
| No queries inside loops | PASS | Ingest: 3 bulk reads + 1 bulk write. Reporting: 3 queries, collapsing in memory |
| Explicit permissions on every view | PASS | `AllowAny` on ingest + settings read (explicitly public per the constitution), `IsAdminUser` on the other five |
| No hardcoded secrets | PASS | Nothing secret involved |
| Models have `__str__`, `Meta.ordering`, `Meta.verbose_name` | PASS | All three (`data-model.md`) |
| Type hints on public signatures | PASS | mypy runs in CI config |
| All code in English | PASS | Except user-facing strings, per CLAUDE.md §1 — matching `IsAdminUser.message` which is Portuguese today |
| Base path `/ipbcb/` not hardcoded | PASS | Relative `path()` entries in `features/songs/urls.py` |
| Functions 4–20 lines, files < 500 | PASS | Enforced by the file split below; the ingest service is the risk and is split into decide/persist |
| Every new function gets a test | PASS | Unit tests for the pure collapse and clock rules, integration tests per endpoint |
| Mock I/O with named fake classes | PASS | `FakeHymnalHistoryRepository`, `FrozenClock` — no inline stubs |

**One item needs a decision recorded rather than a checkbox** — the unauthenticated *write*
endpoint. The constitution permits it ("no endpoint bypasses auth unless explicitly marked public")
and it is explicitly marked, but every other `AllowAny` endpoint in the project is read-only. See
Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-hymnal-view-history/
├── plan.md                  # This file
├── spec.md                  # Feature specification
├── research.md              # Phase 0 output — 12 decisions
├── data-model.md            # Phase 1 output — 3 models + derived Occurrence + 8 DTOs
├── quickstart.md            # Phase 1 output — 12 end-to-end validation scenarios
├── contracts/               # Phase 1 output
│   ├── ingest-endpoint.md
│   ├── reporting-endpoints.md
│   └── settings-and-windows-endpoints.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
server/
├── config/
│   ├── di.py                                    # Update: repository, 3 services, Clock, wiring
│   └── settings/base.py                         # Update: hymnal_ingest throttle rate, NUM_PROXIES
├── core/
│   ├── domain/exceptions.py                     # Update: 3 new domain exceptions
│   └── time/clock.py                            # New: Clock protocol + SystemClock (research R-05)
└── features/songs/
    ├── models/
    │   ├── hymnal_history.py                    # New: 3 models
    │   └── __init__.py                          # Update: re-export
    ├── migrations/
    │   ├── 0004_hymnalhistory...py              # New: schema, name as generated
    │   ├── 0005_..._window_grace_minutes.py     # New: generated
    │   └── 0006_seed_service_windows.py         # New: data migration, reason documented
    ├── hymnal_history_dtos.py                   # New: 8 Pydantic DTOs
    ├── repositories/
    │   ├── interfaces.py                        # Update: HymnalHistoryRepository protocol
    │   └── hymnal_history_repository.py         # New: every ORM query for this feature
    ├── services/
    │   ├── hymnal_history_ingest_service.py     # New: idempotency, collapse, clock validation
    │   ├── hymnal_history_occurrences.py        # New: pure collapse functions, no I/O
    │   ├── hymnal_history_report_service.py     # New: occurrences + top hymns
    │   └── hymnal_history_config_service.py     # New: settings + service window CRUD
    ├── serializers/
    │   └── hymnal_history_serializers.py        # New: request/response/query-param serializers
    ├── views/
    │   └── hymnal_history.py                    # New: 5 APIViews
    ├── urls.py                                  # Update: 7 new paths
    ├── admin.py                                 # Update: register the 3 models
    └── tests/
        ├── unit/
        │   ├── test_hymnal_history_occurrences.py   # New: collapse rules, no DB
        │   ├── test_hymnal_history_ingest_rules.py  # New: clock + dedup + collapse decisions
        │   └── test_hymnal_history_dtos.py          # New: DTO validation
        └── integration/
            ├── test_hymnal_history_ingest_api.py    # New
            ├── test_hymnal_history_reports_api.py   # New
            └── test_hymnal_history_admin_api.py     # New: settings + service windows
```

**Structure Decision**: files drop into the packages `features/songs` already has, prefixed
`hymnal_history_`. No new Django app (would force a cross-feature import of `Hymn`), no restructuring
of existing files. `core/time/clock.py` is the one addition outside the feature — it is
project-wide infrastructure, belongs in `core/` by the same rule that puts exceptions there, and is
what makes clock validation testable (research R-01, R-05).

## Implementation Order

Each step leaves the suite green. Steps 2–4 are the MVP (User Story 1); the rest layer on.

1. **Foundation** — `core/time/clock.py`, the 3 models, migration `0004`, admin registration,
   `models/__init__.py` re-export. Verifies against an empty database before any behaviour exists.
2. **Repository** — `HymnalHistoryRepository` protocol + Django implementation, including the
   `get_or_create(id=1)` settings materialisation and the bulk collapse-candidate lookup.
3. **Ingest** — DTOs, the pure decision functions, `HymnalHistoryIngestService`, serializer, view,
   URL, throttle rate and `NUM_PROXIES`, DI registration. **Delivers User Story 1 (P1).**
4. **Reporting** — pure occurrence collapsing (`hymnal_history_occurrences.py`) first with unit
   tests, then `HymnalHistoryReportService`, the two views and their query-param serializers.
   **Delivers User Stories 2 and 3 (P2, P3).**
5. **Configuration** — `HymnalHistoryConfigService`, settings GET/PATCH, service window CRUD.
   **Delivers User Stories 4 and 5 (P4, P5).**
6. **Seed migration `0006`** — the church's four real windows, confirmed 2026-08-07 (research R-11),
   plus the `window_grace_minutes` setting behind it (R-13). Done last because nothing depends on
   it: with no windows the dashboard already falls back to hymn + calendar day.
7. **Regression pass** — full `pytest` and `mypy`, plus `quickstart.md` step 12 confirming the
   Sunday repertoire flow is untouched.

The pure functions in steps 3 and 4 are written and unit-tested **before** the services that call
them — they hold every rule that is easy to get subtly wrong (window matching, weekday convention,
intra-batch collapse) and they need no database to test.

## Complexity Tracking

> Deviations that need justification rather than a passing checkbox.

| Decision | Why needed | Simpler alternative rejected because |
|----------|------------|-------------------------------------|
| Unauthenticated `POST` ingest | Most members use the hymnal without logging in; requiring auth would collect a biased, largely empty history — the feature would answer the wrong question | Requiring a JWT is simpler and safer, but defeats the purpose. Compensating controls: `600/hour` scoped throttle, `max_batch_size` cap, required `device_id`, `client_event_id` idempotency, strict per-event validation, and no sensitive data in the payload |
| `ServiceWindow` duplicated instead of read from `schedule` | The constitution forbids features importing from each other | Reading the existing schedule would avoid a second source of truth, but is a direct constitution violation. The duplication is explicitly sanctioned by the spec |
| Occurrence collapsing in Python, not SQL | The rule is business logic, is timezone-dependent, and must stay unit-testable without a database; the feature also avoids adding a second PostgreSQL-only query | Full ORM aggregation is one query, but needs a correlated join with timezone conversion in the predicate. Bounded safely by the 366-day cap (research R-04) |
| New `core/time/clock.py` | Clock validation cannot be tested repeatably against the real clock; CLAUDE.md §7 requires injected, project-owned wrappers | Calling `timezone.now()` inline is fewer files, but makes the future-tolerance and max-age rules untestable without patching globals |
| `hymnal_history_dtos.py` beside `dtos.py` rather than a `dtos/` package | Keeps the change additive — no existing import path moves | Converting `dtos.py` into a package is tidier, but is a refactor of working code and would touch the Sunday-plays flow this feature must not disturb |

## Post-Design Constitution Re-Check

Re-evaluated after `data-model.md` and `contracts/` were written:

- **No new violations.** The design added `core/time/clock.py` outside the feature — justified above
  and consistent with `core/` holding cross-cutting infrastructure.
- **Query budget confirmed** against the contracts: ingest is 4 queries for any batch size;
  occurrences is 3; top-hymns is 3. No `select_related` needed because reporting reads
  `.values_list` rather than model instances.
- **Two pre-existing gaps surfaced** that this feature depends on and should fix alongside it
  (research R-02): `NUM_PROXIES` is unset behind nginx, which currently lets a client-supplied
  `X-Forwarded-For` header bypass *every* rate limit including the login throttle; and no `CACHES`
  is configured, so throttle counters are per-process. The first is a real security fix and is
  included in step 3. The second is recorded as an accepted, understood approximation.
- **Spec refinement recorded**: rejection reasons are stable snake_case codes rather than prose
  (research R-07). This narrows FR-009's "a reason" — it does not contradict it.
