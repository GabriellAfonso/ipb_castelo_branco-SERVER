---

description: "Task list for Hymnal View History"
---

# Tasks: Hymnal View History

**Input**: Design documents from `specs/006-hymnal-view-history/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Test tasks are included and are **not optional here** — CLAUDE.md §10 requires a test for
every new function, and the spec's Architecture section repeats it. Unit tests for the pure rule
functions are written *before* the services that call them (plan.md, Implementation Order).

**Organization**: grouped by user story so each is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different file, no dependency on an incomplete task
- **[Story]**: which user story the task serves (US1…US5)
- Every task names its exact file path

## Path Conventions

Django project rooted at `server/`. Feature code lives in `server/features/songs/`; cross-cutting
infrastructure in `server/core/`; container and settings in `server/config/`.

**Two shared files are serialization points** — `server/config/di.py` and
`server/features/songs/urls.py` are touched by nearly every story, so tasks that edit them are never
marked `[P]`, even when the rest of that story is parallelizable.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: cross-cutting groundwork that is not specific to any story

- [X] T001 [P] Set `NUM_PROXIES = 1` in `server/config/settings/base.py` so DRF derives the throttle key from the real client IP behind nginx instead of a client-supplied `X-Forwarded-For` (research R-02; this also fixes the existing `login` throttle bypass)
- [X] T002 [P] Create `server/core/time/__init__.py` and `server/core/time/clock.py` with a `Clock` protocol exposing `now() -> datetime` and a `SystemClock` implementation returning `django.utils.timezone.now()` (research R-05)
- [X] T003 [P] Add unit test in `server/core/tests/unit/test_clock.py` asserting `SystemClock.now()` returns an aware datetime in UTC
- [X] T004 [P] Add domain exceptions to `server/core/domain/exceptions.py`: `ServiceWindowNotFoundError(NotFoundError)` (carries `window_id`), `BatchTooLargeError(ValidationError)` (carries `size` and `max_size`), `ReportRangeError(ValidationError)` (carries `from_date`, `to_date` and the reason). Each message names the offending value and the expected shape per CLAUDE.md §8

**Checkpoint**: infrastructure in place; nothing behavioural yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: models, persistence and DTOs that **every** user story depends on

**⚠️ CRITICAL**: no user story work can begin until this phase is complete

- [X] T005 Create the three models in `server/features/songs/models/hymnal_history.py` — `HymnalViewEvent`, `ServiceWindow`, `HymnalHistorySettings` — with the exact fields, `Meta.ordering`, `Meta.verbose_name`, `__str__`, indexes and check constraints from [data-model.md](data-model.md). **Weekday is `0 = Monday … 6 = Sunday`; Sunday is `6`** (research R-11)
- [X] T006 Re-export the three models from `server/features/songs/models/__init__.py` following the existing `X as X` style
- [X] T007 Generate the schema migration with `python manage.py makemigrations songs` → `server/features/songs/migrations/0004_hymnalhistorysettings_servicewindow_hymnalviewevent.py`. Do not hand-write it (CLAUDE.md §5). Verify it contains both check constraints and both indexes
- [X] T008 [P] Register the three models in `server/features/songs/admin.py`
- [X] T009 [P] Add unit tests in `server/features/songs/tests/unit/test_hymnal_history_models.py` covering: `__str__` on each model, the `end_time > start_time` constraint rejecting an invalid window, the `weekday` 0–6 constraint, and the `id=1` singleton constraint rejecting a second settings row
- [X] T010 [P] Create the 8 Pydantic DTOs in `server/features/songs/hymnal_history_dtos.py`, all extending `StrictBaseModel` — `HymnViewEventInput`, `RejectedEventDTO`, `IngestResultDTO`, `OccurrenceDTO`, `TopHymnDTO`, `HymnalHistorySettingsDTO`, `ServiceWindowDTO`, `ReportRangeDTO` ([data-model.md](data-model.md))
- [X] T011 [P] Add unit tests in `server/features/songs/tests/unit/test_hymnal_history_dtos.py` asserting `extra="forbid"` rejects unknown keys, that a naive `viewed_at` is rejected, and that a negative `duration_seconds` is rejected
- [X] T012 Add the `HymnalHistoryRepository` protocol to `server/features/songs/repositories/interfaces.py` with fully typed signatures for: `get_existing_client_event_ids`, `get_collapse_candidates`, `get_hymns_by_ids`, `bulk_create_events`, `list_events_in_range`, `list_active_service_windows`, `list_service_windows`, `get_service_window`, `create_service_window`, `update_service_window`, `delete_service_window`, `get_settings`, `update_settings`
- [X] T013 Implement `DjangoHymnalHistoryRepository` in `server/features/songs/repositories/hymnal_history_repository.py` — the only place this feature touches the ORM. `get_settings()` uses `get_or_create(id=1, defaults=...)` (research R-06); `list_events_in_range()` returns `.values_list("hymn_id", "viewed_at", "device_id")`; `get_collapse_candidates()` takes the batch's `(hymn_id, device_id)` pairs and one bounding time interval in a single query (research R-03, R-04)
- [X] T014 [P] Create named test fakes in `server/features/songs/tests/fakes.py` — `FakeHymnalHistoryRepository` (in-memory, implements the full protocol) and `FrozenClock` (returns a fixed aware datetime). Named classes, not inline stubs (CLAUDE.md §10)
- [X] T015 Register in `server/config/di.py`: `clock = providers.Singleton(SystemClock)` and `hymnal_history_repository = providers.Factory(DjangoHymnalHistoryRepository)`, and add `"features.songs.views.hymnal_history"` to `wiring_config.modules`

**Checkpoint**: schema migrates, models are queryable, persistence and DTOs exist. User stories can now proceed — in parallel if staffed.

---

## Phase 3: User Story 1 — Ingest (Priority: P1) 🎯 MVP

**Goal**: the app can sync buffered hymn views, safely and repeatedly, with or without a login.

**Independent Test**: POST a batch and confirm every id comes back in `accepted` or `rejected`; re-POST the identical batch and confirm no duplicate rows and the same `accepted` list.

**Contract**: [contracts/ingest-endpoint.md](contracts/ingest-endpoint.md)

### Tests for User Story 1

> Write these first. The pure-rule tests need no database and must fail before T019/T020 exist.

- [X] T016 [P] [US1] Unit tests for the pure ingest decision rules in `server/features/songs/tests/unit/test_hymnal_history_ingest_rules.py`: unknown hymn → `unknown_hymn`; `viewed_at` beyond `now + future_tolerance_minutes` → `viewed_at_in_future`; older than `max_past_days` → `viewed_at_too_old`; duplicate `client_event_id` → accepted-not-stored; same hymn+device inside the collapse window → accepted-not-stored; **intra-batch** collapse of two events in the same payload; the same `client_event_id` twice in one payload; a duration below `min_seconds_to_count` **is stored** (FR-011). Uses `FrozenClock` from T014
- [X] T017 [P] [US1] Integration tests in `server/features/songs/tests/integration/test_hymnal_history_ingest_api.py`: anonymous POST stores with `user = null`; POST with a valid JWT attributes the user; one bad event does not block the rest (FR-007); empty batch → `201` with two empty lists; batch over `max_batch_size` → `400` with nothing stored; re-POST is idempotent; response is always `201`

### Implementation for User Story 1

- [X] T018 [P] [US1] Add `"hymnal_ingest": "600/hour"` to `DEFAULT_THROTTLE_RATES` in `server/config/settings/base.py` (research R-02)
- [X] T019 [US1] Implement the pure decision functions in `server/features/songs/services/hymnal_history_ingest_rules.py` — no I/O, no ORM: `validate_clock(event, now, settings)`, and a `decide_batch(events, known_ids, collapse_index, known_hymn_ids, now, settings)` returning `(to_store, accepted_ids, rejected)`. Events are sorted by `viewed_at` and a running `(hymn_id, device_id) -> last_kept` map handles intra-batch collapse (research R-03). Reason codes are the stable snake_case set from the contract (research R-07)
- [X] T020 [US1] Implement `HymnalHistoryIngestService` in `server/features/songs/services/hymnal_history_ingest_service.py`, constructor-injected with `repository` and `clock`. `ingest(events: list[HymnViewEventInput], user_id: int | None) -> IngestResultDTO` does the 3 bulk reads, calls `decide_batch`, then one `bulk_create(..., ignore_conflicts=True)` inside a transaction. Raises `BatchTooLargeError` when the batch exceeds `max_batch_size`. Never imports an HTTP object
- [X] T021 [P] [US1] Create the ingest serializers in `server/features/songs/serializers/hymnal_history_serializers.py` — envelope validation only (`events` present, a list, within `max_batch_size`) plus the response serializer. Per-event validation stays in the service so one bad event cannot fail the batch (research R-09)
- [X] T022 [US1] Implement `HymnalHistoryIngestAPI` in `server/features/songs/views/hymnal_history.py` — `permission_classes = [AllowAny]`, `throttle_classes = [ScopedRateThrottle]`, `throttle_scope = "hymnal_ingest"`, `@inject` the service, derive `user_id` from `request.user` when authenticated and pass it as `int | None`. Returns `201`
- [X] T023 [US1] Register `hymnal_history_ingest_service` in `server/config/di.py` (depends on the repository and clock from T015)
- [X] T024 [US1] Add `path("api/hymnal-history/events/", ..., name="hymnal_history_events")` to `server/features/songs/urls.py`
- [X] T025 [P] [US1] Add the structured JSON ingest summary log in `server/features/songs/services/hymnal_history_ingest_service.py` — one line per request with `received`, `stored`, `deduplicated`, `collapsed`, `rejected` counts and rejection codes with counts. No per-event logging (research R-12)

**Checkpoint**: User Story 1 fully functional. Run [quickstart.md](quickstart.md) steps 1–6. **This is the MVP — deployable on its own.**

---

## Phase 4: User Story 2 — Occurrences dashboard (Priority: P2)

**Goal**: leadership sees which hymns were sung in a period, collapsed per congregation rather than per person.

**Independent Test**: create `HymnalViewEvent` rows directly via the ORM (no ingest endpoint needed), then request a range and confirm the collapsing. This is what keeps US2 independent of US1.

**Contract**: [contracts/reporting-endpoints.md](contracts/reporting-endpoints.md)

### Tests for User Story 2

- [X] T026 [P] [US2] Unit tests for the pure occurrence rules in `server/features/songs/tests/unit/test_hymnal_history_occurrences.py`: three devices in one window → one occurrence, `device_count = 3`; the same hymn in a morning and an evening window → two occurrences; an event outside every window → collapsed by calendar day with `service_window_id = None`; **overlapping windows → the earliest-starting active one wins** (FR-016); an event exactly at `start_time` is inside, exactly at `end_time` is outside; a Sunday event maps to `weekday == 6`; UTC-stored timestamps near midnight bucket by *local* date; bucket labels for all four `group_by` values; the occurrence count is identical across all four groupings (FR-018)
- [X] T027 [P] [US2] Integration tests in `server/features/songs/tests/integration/test_hymnal_history_reports_api.py`: admin gets `200`; anonymous gets `401`; a non-admin authenticated user gets `403`; `from` after `to` → `400`; a span over 366 days → `400`; default range is the last 30 days; deleting a `ServiceWindow` regroups occurrences without changing the stored event count (FR-023)

### Implementation for User Story 2

- [X] T028 [US2] Implement the pure collapsing module `server/features/songs/services/hymnal_history_occurrences.py` — `match_window(local_dt, windows)` and `collapse_events(events, windows, group_by)` returning `list[OccurrenceDTO]`. No ORM, no I/O, no `timezone.now()`. Timezone conversion via `django.utils.timezone.localtime` at the boundary (research R-04, R-05)
- [X] T029 [US2] Implement `HymnalHistoryReportService.list_occurrences(range: ReportRangeDTO) -> list[OccurrenceDTO]` in `server/features/songs/services/hymnal_history_report_service.py` — validates the range (raises `ReportRangeError` on inverted or over-366-day spans), converts inclusive local dates to the half-open aware interval, then calls the repository and `collapse_events`
- [X] T030 [US2] Add the occurrences query-param and response serializers to `server/features/songs/serializers/hymnal_history_serializers.py` — `from`/`to` as `DateField`, `group_by` as a `ChoiceField` defaulting to `service`; `from` stays `from` on the wire despite being a Python keyword (research R-10)
- [X] T031 [US2] Implement `HymnalHistoryOccurrencesAPI` in `server/features/songs/views/hymnal_history.py` with `permission_classes = [IsAdminUser]` from `core/http/permissions.py`
- [X] T032 [US2] Register `hymnal_history_report_service` in `server/config/di.py`
- [X] T033 [US2] Add `path("api/hymnal-history/occurrences/", ..., name="hymnal_history_occurrences")` to `server/features/songs/urls.py`

**Checkpoint**: User Stories 1 and 2 both work independently. Run quickstart steps 7–8.

---

## Phase 5: User Story 3 — Top hymns ranking (Priority: P3)

**Goal**: an all-time (or ranged) chart of the most-sung hymns, counting occurrences rather than raw events.

**Independent Test**: seed a known set of events, request the ranking, confirm counts and descending order, and confirm hymns with no occurrences are absent.

**Contract**: [contracts/reporting-endpoints.md](contracts/reporting-endpoints.md)

### Tests for User Story 3

- [X] T034 [P] [US3] Unit tests in `server/features/songs/tests/unit/test_hymnal_history_top_hymns.py`: five devices contributing to one occurrence count as 1 (FR-020); hymns with zero occurrences are omitted; ordering is `occurrence_count` desc then hymn number asc; an optional range filters correctly; omitting both dates covers all time
- [X] T035 [P] [US3] Integration tests in `server/features/songs/tests/integration/test_hymnal_history_reports_api.py` (extend T027's file): admin `200`, non-admin `403`, anonymous `401`, ranged vs all-time results differ as expected

### Implementation for User Story 3

- [X] T036 [US3] Add `HymnalHistoryReportService.top_hymns(from_date: date | None, to_date: date | None) -> list[TopHymnDTO]` to `server/features/songs/services/hymnal_history_report_service.py`, reusing `collapse_events` from T028 so the count means the same thing in both endpoints. The 366-day cap does **not** apply here (contract)
- [X] T037 [US3] Add the top-hymns query-param and response serializers to `server/features/songs/serializers/hymnal_history_serializers.py`
- [X] T038 [US3] Implement `HymnalHistoryTopHymnsAPI` in `server/features/songs/views/hymnal_history.py` with `permission_classes = [IsAdminUser]`
- [X] T039 [US3] Add `path("api/hymnal-history/top-hymns/", ..., name="hymnal_history_top_hymns")` to `server/features/songs/urls.py`

**Checkpoint**: all three reading and writing stories work. Run quickstart step 9.

---

## Phase 6: User Story 4 — Tunable settings (Priority: P4)

**Goal**: an admin changes collection behaviour without a deploy; the app reads the threshold without a login.

**Independent Test**: read the settings anonymously, PATCH one value as an admin, read it back, and confirm stored history is untouched.

**Contract**: [contracts/settings-and-windows-endpoints.md](contracts/settings-and-windows-endpoints.md)

### Tests for User Story 4

- [X] T040 [P] [US4] Integration tests in `server/features/songs/tests/integration/test_hymnal_history_admin_api.py`: anonymous `GET` → `200` with the defaults on an empty database (FR-025, research R-06); anonymous `PATCH` → `401`; non-admin `PATCH` → `403`; admin `PATCH` → `200` with the new value; each field at 0, negative and above its maximum → `400` with `field_errors` naming the field, the value and the range (FR-026); **after a PATCH, the top-hymns counts and the stored event rows are unchanged** (FR-027)

### Implementation for User Story 4

- [X] T041 [US4] Implement `HymnalHistoryConfigService.get_settings()` and `update_settings(dto)` in `server/features/songs/services/hymnal_history_config_service.py`
- [X] T042 [US4] Add the settings serializer to `server/features/songs/serializers/hymnal_history_serializers.py` with the per-field min/max from [data-model.md](data-model.md) and error messages naming the field, the offending value and the accepted range
- [X] T043 [US4] Implement `HymnalHistorySettingsAPI` in `server/features/songs/views/hymnal_history.py` — `get_permissions()` returns `[AllowAny]` for `GET` and `[IsAdminUser]` for `PATCH` on the same view
- [X] T044 [US4] Register `hymnal_history_config_service` in `server/config/di.py`
- [X] T045 [US4] Add `path("api/hymnal-history/settings/", ..., name="hymnal_history_settings")` to `server/features/songs/urls.py`

**Checkpoint**: settings readable and tunable. Run quickstart step 10.

---

## Phase 7: User Story 5 — Service window CRUD (Priority: P5)

**Goal**: an admin maintains the church's service times from the app.

**Independent Test**: create, list, update and delete a window as an admin; confirm validation rejects `end_time <= start_time` and a weekday outside 0–6.

**Contract**: [contracts/settings-and-windows-endpoints.md](contracts/settings-and-windows-endpoints.md)

### Tests for User Story 5

- [X] T046 [P] [US5] Integration tests in `server/features/songs/tests/integration/test_hymnal_history_admin_api.py` (extend T040's file): admin can list, create, retrieve, update and delete; `end_time <= start_time` → `400` naming both values; `weekday = 7` and `weekday = -1` → `400` naming the value and the range; a missing id → `404` with `error_code: "NOT_FOUND"`; non-admin → `403`; **deleting a window leaves every `HymnalViewEvent` row intact** (FR-023)

### Implementation for User Story 5

- [X] T047 [US5] Add the service window methods to `server/features/songs/services/hymnal_history_config_service.py` — `list_windows`, `get_window`, `create_window`, `update_window`, `delete_window`, raising `ServiceWindowNotFoundError` (T004) for a missing id
- [X] T048 [US5] Add the service window serializer to `server/features/songs/serializers/hymnal_history_serializers.py` with `validate()` enforcing `end_time > start_time` and `weekday` in 0–6, mirroring the database constraints
- [X] T049 [US5] Implement `ServiceWindowListCreateAPI` and `ServiceWindowDetailAPI` as plain `APIView`s in `server/features/songs/views/hymnal_history.py`, matching the existing `ChordChartListAPI` / `ChordChartDetailAPI` shape — no router, no ViewSet (research R-08)
- [X] T050 [US5] Add `path("api/hymnal-history/service-windows/", ..., name="service_windows")` and `path("api/hymnal-history/service-windows/<int:pk>/", ..., name="service_window_detail")` to `server/features/songs/urls.py`

**Checkpoint**: all five user stories independently functional. Run quickstart step 11.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T051 Write the data migration `server/features/songs/migrations/0006_seed_service_windows.py` seeding the church's four real windows — Terça de Oração (Tue 19:30–20:30), Quinta de Oração (Thu 19:30–20:30), Escola Bíblica Dominical (Sun 09:00–10:00), Culto Dominical (Sun 19:30–21:00) — with the reason at the top of the file (CLAUDE.md §5, which permits hand-written *data* migrations), `get_or_create` by name so it is idempotent, and a reverse deleting only those four. Weekday `0 = Monday … 6 = Sunday`, so Sunday is `6`
- [X] T059 Add `window_grace_minutes` (default 30) to `HymnalHistorySettings`, extend `match_window` in `server/features/songs/services/hymnal_history_occurrences.py` to run past `end_time` by that much, and thread it from the settings through `HymnalHistoryReportService`. Compare on datetimes, not bare times, so a grace period crossing midnight does not wrap (research R-13)
- [X] T060 Add `server/features/songs/tests/integration/test_hymnal_history_seed.py` — the seeded windows match the church's real schedule, and end-to-end grouping works against them including the grace period
- [X] T052 [P] Add `@extend_schema` annotations to every view in `server/features/songs/views/hymnal_history.py`, matching the existing pattern in `server/features/accounts/views/auth.py`, so the public OpenAPI schema documents the new endpoints
- [X] T053 [P] Update `specs/songs/spec.md` — remove the "not yet built" implementation-status note now that the feature exists, and confirm the documented models and endpoints match what shipped (CLAUDE.md §6.2: spec and code go together)
- [X] T054 Run `mypy .` from `server/` and resolve every new error. No `Any`, no bare `dict` in public signatures (CLAUDE.md §8)
- [X] T055 Run `black` over every new and modified file
- [X] T056 Run the full suite: `pytest` from `server/`. The existing `test_register_plays_api.py` and every other songs test must pass **unchanged** (FR-030, SC-008)
- [ ] T057 Walk [quickstart.md](quickstart.md) steps 1–12 against a running server, including step 12 confirming the Sunday repertoire flow is untouched
- [X] T058 Review file sizes and function lengths across the new files against CLAUDE.md §8 (functions 4–20 lines, files under 500). `hymnal_history_serializers.py` and `views/hymnal_history.py` accumulate across five stories and are the likeliest to need splitting

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup (T002's `Clock`, T004's exceptions) — **blocks every user story**
- **User Stories (Phases 3–7)**: all depend only on Phase 2. Can run in parallel if staffed, or sequentially P1 → P5
- **Polish (Phase 8)**: depends on the stories you intend to ship. T051 additionally depends on an answer from the church

### User Story Dependencies

- **US1 (P1)**: independent. No other story needed
- **US2 (P2)**: independent — tests seed `HymnalViewEvent` rows via the ORM rather than through the ingest endpoint
- **US3 (P3)**: reuses `collapse_events` (T028) from US2. **This is the one real cross-story dependency** — deliberate, because the two endpoints must count occurrences identically (FR-020). If US3 is built before US2, T028 moves into US3's phase
- **US4 (P4)**: independent
- **US5 (P5)**: independent. Shares `hymnal_history_config_service.py` with US4, so those two conflict on that file even though neither needs the other

### Within Each User Story

- Unit tests for the pure rule functions are written and failing before those functions exist
- Pure functions → services → serializers → views → URL registration
- DI registration after the service it registers

### Parallel Opportunities

- Phase 1: T001–T004 are four different files — all parallel
- Phase 2: T008, T009, T010, T011, T014 are parallel once T005–T007 land
- Within a story: the test tasks marked `[P]` are parallel with each other
- Across stories: US1, US2, US4 and US5 can be built by different people simultaneously after Phase 2 — but they serialize on `server/config/di.py` and `server/features/songs/urls.py`, and US4/US5 also serialize on `hymnal_history_config_service.py`

---

## Parallel Example: Phase 2 Foundational

```bash
# After T005-T007 (models + migration) land, these four are independent files:
Task: "T008 Register models in server/features/songs/admin.py"
Task: "T009 Model unit tests in server/features/songs/tests/unit/test_hymnal_history_models.py"
Task: "T010 Pydantic DTOs in server/features/songs/hymnal_history_dtos.py"
Task: "T014 Test fakes in server/features/songs/tests/fakes.py"
```

## Parallel Example: User Story 1

```bash
# Write both test files first — neither depends on the other:
Task: "T016 Pure ingest rule unit tests in .../tests/unit/test_hymnal_history_ingest_rules.py"
Task: "T017 Ingest API integration tests in .../tests/integration/test_hymnal_history_ingest_api.py"

# Then the settings change runs alongside the rule implementation:
Task: "T018 Throttle rate in server/config/settings/base.py"
Task: "T019 Pure decision functions in .../services/hymnal_history_ingest_rules.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1: Setup (T001–T004)
2. Phase 2: Foundational (T005–T015) — **blocks everything**
3. Phase 3: User Story 1 (T016–T025)
4. **STOP and VALIDATE**: quickstart steps 1–6
5. Deployable. The app can start collecting history immediately — and since occurrences are derived at read time, **data collected now is fully usable by the dashboards built later**

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → collection works → deploy (**MVP**)
3. US2 → the dashboard the feature exists for → deploy
4. US3 → the ranking chart → deploy
5. US4 → tuning without a deploy → deploy
6. US5 → window maintenance → deploy
7. Phase 8 polish, with T051 done once the church confirms its service times

Collecting before reporting is the right order here, not just the priority order: history has to accumulate before a dashboard has anything to show.

### Parallel Team Strategy

After Phase 2, with three developers: A takes US1, B takes US2 then US3 (they share T028), C takes US4 then US5 (they share a service file). Coordinate merges on `config/di.py` and `features/songs/urls.py` — those two files are touched by every story.

---

## Notes

- `[P]` = different file, no dependency on an incomplete task
- Commit after each task or logical group; spec and code go together in the same commit (CLAUDE.md §6.2)
- **T051 was dropped by decision** — no seed migration. See the task itself for why
- Rejection reason codes are stable API surface — changing one is a breaking change for the app's logging
- The weekday convention (`0 = Monday`, Sunday = `6`) appears in T005 and T026, and whoever creates the windows in production has to use it too. Getting it wrong produces no error — the window just never matches. Note that `schedule` uses a different convention (`1 = Sunday`); reconciling the two is feature 007
