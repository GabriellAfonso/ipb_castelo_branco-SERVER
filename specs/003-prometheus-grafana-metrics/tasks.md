# Tasks: Application Metrics with Prometheus & Grafana

**Input**: Design documents from `specs/003-prometheus-grafana-metrics/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add django-prometheus dependency and create monitoring config directory structure

- [x] T001 Add `django-prometheus` to `requirements.txt` under a `# Monitoring` section
- [x] T002 Create monitoring infrastructure directory structure: `monitoring/prometheus/` and `monitoring/grafana/provisioning/datasources/`, `monitoring/grafana/provisioning/dashboards/`, `monitoring/grafana/dashboards/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Configure django-prometheus in Django settings and URL routing — MUST be complete before any user story

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Add `django_prometheus` to `INSTALLED_APPS` in `server/config/settings/base.py` — add before all other apps (first entry) per django-prometheus docs
- [x] T004 Add `django_prometheus.middleware.PrometheusBeforeMiddleware` as FIRST entry in `MIDDLEWARE` and `django_prometheus.middleware.PrometheusAfterMiddleware` as LAST entry in `MIDDLEWARE` in `server/config/settings/base.py`
- [x] T005 Add `path("", include("django_prometheus.urls"))` to `urlpatterns` in `server/config/urls.py` — exposes `/metrics` endpoint at root level (not behind `/ipbcb/`)

**Checkpoint**: `/metrics` endpoint accessible, returns Prometheus exposition format with basic django-prometheus metrics

---

## Phase 3: User Story 1 - Infrastructure Metrics Collection (Priority: P1)

**Goal**: Django API automatically exposes RED metrics (Rate, Errors, Duration) via django-prometheus middleware

**Independent Test**: Send requests to any API endpoint, then `curl http://localhost:8000/metrics` and verify `django_http_requests_total_by_method_total` and `django_http_requests_latency_seconds_by_view_method` metrics appear with correct labels (method, status, view)

### Implementation for User Story 1

- [x] T006 [US1] Verify RED metrics work end-to-end: start server, hit an endpoint, confirm `/metrics` returns `django_http_requests_total_by_method_total` and `django_http_requests_latency_seconds_by_view_method_bucket` counters — this is auto-instrumented by middleware added in T004, no additional code needed

**Checkpoint**: US1 complete — all API requests automatically counted and timed

---

## Phase 4: User Story 2 - Database Query Monitoring (Priority: P2)

**Goal**: Database query count and duration automatically collected via django-prometheus DB engine wrapper

**Independent Test**: Trigger API endpoints that perform DB queries, then `curl http://localhost:8000/metrics | grep django_db` and verify `django_db_execute_total` and `django_db_execute_duration_seconds` metrics appear

### Implementation for User Story 2

- [x] T007 [US2] Replace database engine `django.db.backends.postgresql` with `django_prometheus.db.backends.postgresql` in `DATABASES["default"]["ENGINE"]` in `server/config/settings/base.py`

**Checkpoint**: US2 complete — all ORM queries automatically counted and timed

---

## Phase 5: User Story 3 - Business Event Tracking (Priority: P3)

**Goal**: Custom counters track logins, schedules, and song interactions in the service layer

**Independent Test**: Perform login, schedule generation, and song play registration, then `curl http://localhost:8000/metrics | grep ipbcb_` and verify all custom counters increment correctly

### Implementation for User Story 3

- [x] T008 [US3] Create `server/core/metrics.py` with all custom Prometheus counters: `ipbcb_login_total` (labels: result, login_type), `ipbcb_schedule_generated_total`, `ipbcb_schedule_saved_total`, `ipbcb_song_plays_registered_total`, `ipbcb_chord_chart_views_total`, `ipbcb_lyrics_views_total` — use `prometheus_client.Counter` with `ipbcb_` namespace prefix
- [x] T009 [P] [US3] Instrument `LoginService.login()` in `server/features/accounts/services/login_service.py` — import counters from `core.metrics`, increment `ipbcb_login_total` with `login_type="credentials"` and `result="success"` on success, `result="failure"` on `InvalidCredentialsError`
- [x] T010 [P] [US3] Instrument `GoogleAuthService.authenticate_google()` in `server/features/accounts/services/google_auth_service.py` — increment `ipbcb_login_total` with `login_type="google"` and `result="success"` on success, `result="failure"` on any auth exception
- [x] T011 [P] [US3] Instrument `RegisterPlaysService` in `server/features/songs/services/register_plays_service.py` — increment `ipbcb_song_plays_registered_total` on successful play registration
- [x] T012 [P] [US3] Instrument `SongService.list_chord_charts()` and `SongService.list_lyrics()` in `server/features/songs/services/song_service.py` — increment `ipbcb_chord_chart_views_total` and `ipbcb_lyrics_views_total` respectively
- [x] T013 [P] [US3] Instrument `generate_monthly_schedule_preview()` in `server/features/schedule/services/monthly_scheduler.py` — increment `ipbcb_schedule_generated_total` on successful generation

**Checkpoint**: US3 complete — all business events tracked as Prometheus counters

---

## Phase 6: User Story 4 - Metrics Visualization (Priority: P4)

**Goal**: Prometheus scrapes Django metrics, Grafana displays pre-provisioned dashboard

**Independent Test**: `docker-compose up`, open `http://localhost:9090/targets` to verify Prometheus target is UP, open `http://localhost:3000` to verify Grafana dashboard shows panels with data

### Implementation for User Story 4

- [x] T014 [US4] Create Prometheus scrape config at `monitoring/prometheus/prometheus.yml` — global scrape interval 15s, job `django` targeting `ipbcb_server:8000` at path `/metrics`
- [x] T015 [P] [US4] Create Grafana datasource provisioning at `monitoring/grafana/provisioning/datasources/prometheus.yml` — configure Prometheus at `http://prometheus:9090` as default datasource
- [x] T016 [P] [US4] Create Grafana dashboard provisioning config at `monitoring/grafana/provisioning/dashboards/dashboard.yml` — point to `/var/lib/grafana/dashboards` directory
- [x] T017 [US4] Create Grafana dashboard JSON at `monitoring/grafana/dashboards/ipbcb-overview.json` — panels: request rate by status, latency p50/p95/p99, error rate (4xx+5xx), DB query duration, and business counters (login, schedule, song plays)
- [x] T018 [US4] Add `prometheus` and `grafana` services to `docker-compose.yml` — Prometheus on port 9090 with volume mount for config and data, Grafana on port 3000 with volume mounts for provisioning and dashboards, both depend on `ipbcb_server`
- [x] T019 [US4] Add `.env.example` entries for Grafana admin credentials (`GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_PASSWORD`) with placeholder values

**Checkpoint**: US4 complete — full monitoring stack running with pre-configured dashboard

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [x] T020 Run full quickstart.md validation: start all containers, verify `/metrics` returns data, Prometheus target UP, Grafana dashboard loads with panels
- [x] T021 Update `specs/003-prometheus-grafana-metrics/spec.md` status from Draft to Implemented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001 for dependency)
- **US1 (Phase 3)**: Depends on Phase 2 (middleware already does the work)
- **US2 (Phase 4)**: Depends on Phase 2 — can run parallel with US1
- **US3 (Phase 5)**: Depends on Phase 2 — can run parallel with US1/US2
- **US4 (Phase 6)**: Depends on Phase 2 — can run parallel with US1/US2/US3 (Docker infra is independent)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: No code needed beyond Phase 2 middleware — auto-instrumented
- **US2 (P2)**: Single config change (DB engine) — independent of US1
- **US3 (P3)**: Depends on Phase 2 for `/metrics` endpoint — independent of US1/US2
- **US4 (P4)**: Docker infrastructure — independent of US1/US2/US3 code changes

### Within User Story 3

- T008 (metrics definitions) MUST complete before T009-T013
- T009, T010, T011, T012, T013 can all run in parallel (different files)

### Parallel Opportunities

- After Phase 2: US1, US2, US3, US4 can all proceed in parallel
- Within US3: T009, T010, T011, T012, T013 are all [P] (different service files)
- Within US4: T015, T016 are [P] (different Grafana config files)

---

## Parallel Example: User Story 3

```bash
# After T008 (metrics.py) is complete, launch all service instrumentation in parallel:
Task: "T009 Instrument LoginService in server/features/accounts/services/login_service.py"
Task: "T010 Instrument GoogleAuthService in server/features/accounts/services/google_auth_service.py"
Task: "T011 Instrument RegisterPlaysService in server/features/songs/services/register_plays_service.py"
Task: "T012 Instrument SongService in server/features/songs/services/song_service.py"
Task: "T013 Instrument MonthlyScheduler in server/features/schedule/services/monthly_scheduler.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T005)
3. Verify Phase 3: US1 (T006) — RED metrics auto-collected
4. **STOP and VALIDATE**: `curl /metrics` returns request rate/latency/error metrics
5. Deploy if ready — immediate observability value

### Incremental Delivery

1. Setup + Foundational → `/metrics` endpoint live
2. US1 (auto) → RED metrics visible → validate
3. US2 (one config line) → DB metrics visible → validate
4. US3 (service instrumentation) → Business metrics visible → validate
5. US4 (Docker infra) → Full dashboard → validate with quickstart.md

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- US1 and US2 are essentially config-only — no custom code
- US3 is the bulk of custom code (metrics.py + 5 service modifications)
- US4 is all infrastructure config (Docker, Prometheus, Grafana)
- No test tasks generated — not explicitly requested in spec
- Commit after each phase or logical group
