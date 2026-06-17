# Tasks: Structured JSON Logging

**Input**: Design documents from `specs/002-structured-json-logging/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/log-format.md

**Organization**: Tasks grouped by user story. All 3 stories share foundational infrastructure (Phase 2), then each story validates a different aspect of the logging system.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add dependency and create package structure

- [x] T001 Add `python-json-logger>=3.0,<4.0` to `requirements.txt`
- [x] T002 Create `server/core/logging/__init__.py` package init

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core logging infrastructure that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement `RequestIdFilter` and `request_id` ContextVar in `server/core/logging/context.py` — define `ContextVar[str | None]` for request_id, create `logging.Filter` subclass that reads from ContextVar and sets `request_id` on every log record (default to `None` outside request context). Include helper functions `set_request_id(id)` and `get_request_id() -> str | None`.
- [x] T004 Add `LOGGING` dictConfig to `server/config/settings/base.py` — JSON formatter via `pythonjsonlogger.json.JsonFormatter`, single `console` handler writing to stdout, `request_id` filter on handler, root logger at INFO, Django loggers (`django.request`, `django.server`, `django.db.backends`) at WARNING. Use exact config from plan.md section "4. LOGGING Configuration".
- [x] T005 Implement `RequestLoggingMiddleware` in `server/core/http/middleware.py` — Django middleware that: (1) generates UUID4 request_id and sets it in ContextVar, (2) adds `X-Request-ID` response header, (3) logs request start with method, path, client_ip, user_id, (4) logs request end with method, path, status_code, duration_ms, user_id. Extract client IP from `HTTP_X_FORWARDED_FOR` (first IP) with fallback to `REMOTE_ADDR`. Read `user_id` from `request.user` after response (handles auth middleware ordering). Reset ContextVar in finally block.
- [x] T006 Register `RequestLoggingMiddleware` in `MIDDLEWARE` list in `server/config/settings/base.py` — insert `"core.http.middleware.RequestLoggingMiddleware"` as second entry (after `SecurityMiddleware`, before `SessionMiddleware`)

**Checkpoint**: JSON logging infrastructure complete. All log output is now JSON with request_id propagation.

---

## Phase 3: User Story 1 — Trace an Error by Request ID (Priority: P1) MVP

**Goal**: Developer can trace any error end-to-end using `X-Request-ID` from Android client

**Independent Test**: Make API call, capture `X-Request-ID` header, verify all log lines for that request share same `request_id` in JSON format

### Tests for User Story 1

- [x] T007 [P] [US1] Write unit tests for `RequestIdFilter` in `server/core/tests/unit/test_logging_context.py` — test filter injects `request_id` when ContextVar is set, test filter sets `None` when ContextVar is unset (outside request), test `set_request_id`/`get_request_id` helpers
- [x] T008 [P] [US1] Write unit tests for `RequestLoggingMiddleware` in `server/core/tests/unit/test_request_logging_middleware.py` — test `X-Request-ID` header present on response with valid UUID4, test request_id is unique per request, test ContextVar is reset after request completes, test middleware handles exceptions in view gracefully (still logs + sets header)

**Checkpoint**: US1 validated — request_id flows from middleware through all loggers to response header

---

## Phase 4: User Story 2 — Monitor Request Traffic in Docker (Priority: P2)

**Goal**: Operator sees structured JSON lines with method, path, status_code, duration_ms for every request

**Independent Test**: Make several API calls, verify each produces JSON log line at request completion with all required fields

### Tests for User Story 2

- [x] T009 [P] [US2] Add traffic monitoring tests to `server/core/tests/unit/test_request_logging_middleware.py` — test request start log contains method, path, client_ip fields; test request end log contains method, path, status_code, duration_ms fields; test duration_ms is positive number; test user_id is included for authenticated requests; test user_id is null for unauthenticated requests; test client_ip extracted from X-Forwarded-For header; test client_ip fallback to REMOTE_ADDR

**Checkpoint**: US2 validated — all request traffic produces queryable JSON with timing data

---

## Phase 5: User Story 3 — Existing Exception Logging Benefits Automatically (Priority: P3)

**Goal**: Existing `custom_exception_handler` log calls output as JSON with request_id — zero code changes to exception handler

**Independent Test**: Trigger domain exception, verify log line is valid JSON containing `request_id`, `level`, and error details

### Tests for User Story 3

- [x] T010 [US3] Add exception handler integration tests to `server/core/tests/unit/test_request_logging_middleware.py` — test that `custom_exception_handler` WARNING logs include `request_id` from ContextVar when called during a request; test that ERROR logs with traceback are contained within JSON structure (not separate lines); verify zero changes to `server/core/http/exceptions.py` (FR-012)

**Checkpoint**: US3 validated — existing logging call sites produce structured JSON automatically

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases and final validation

- [x] T011 [P] Handle edge case: logging outside request context (management commands, startup) — verify `RequestIdFilter` sets `request_id` to `None` without raising errors. Add test case in `server/core/tests/unit/test_logging_context.py`
- [x] T012 [P] Handle edge case: middleware exception during processing — ensure `RequestLoggingMiddleware` catches its own errors in a try/finally so ContextVar is always reset and partial logs still emitted. Add test in `server/core/tests/unit/test_request_logging_middleware.py`
- [ ] T013 *(requires running server — manual validation)* Run `specs/002-structured-json-logging/quickstart.md` validation scenarios against running server

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1. BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — tests validate request_id tracing
- **US2 (Phase 4)**: Depends on Phase 2 — tests validate traffic monitoring fields
- **US3 (Phase 5)**: Depends on Phase 2 — tests validate exception handler integration
- **Polish (Phase 6)**: Depends on Phases 3-5

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. No dependencies on other stories.
- **US2 (P2)**: Can start after Phase 2. Independent of US1.
- **US3 (P3)**: Can start after Phase 2. Independent of US1/US2.
- All 3 stories can run in parallel after Phase 2 completes.

### Within Each User Story

- Tests written first, verify they reference correct modules
- No model/service/endpoint split needed — this feature is infrastructure-only

### Parallel Opportunities

- T001 and T002 can run in parallel (Setup)
- T003 and T004 can run in parallel (different files: `context.py` vs `base.py`)
- T007 and T008 can run in parallel (different test files)
- US1, US2, US3 test phases can all run in parallel after Phase 2
- T011 and T012 can run in parallel (different edge cases, different files)

---

## Parallel Example: Foundational Phase

```bash
# These touch different files — run in parallel:
Task T003: "Implement RequestIdFilter in server/core/logging/context.py"
Task T004: "Add LOGGING dictConfig to server/config/settings/base.py"
```

## Parallel Example: User Story Tests

```bash
# After Phase 2, all story tests can run in parallel:
Task T007: "Unit tests for RequestIdFilter in test_logging_context.py"
Task T008: "Unit tests for RequestLoggingMiddleware in test_request_logging_middleware.py"
Task T009: "Traffic monitoring tests in test_request_logging_middleware.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001, T002)
2. Complete Phase 2: Foundational (T003-T006)
3. Complete Phase 3: US1 tests (T007, T008)
4. **STOP and VALIDATE**: `X-Request-ID` header present, all logs are JSON with request_id
5. Deploy if ready — core traceability working

### Incremental Delivery

1. Setup + Foundational -> JSON logging active, middleware running
2. US1 tests -> Traceability validated (MVP!)
3. US2 tests -> Traffic monitoring validated
4. US3 tests -> Exception handler backward compatibility validated
5. Polish -> Edge cases covered, quickstart validated

---

## Notes

- This feature is infrastructure-only — no models, services, or views created
- All 3 user stories share same foundational code (Phase 2); stories differ only in what they test/validate
- T005 is the largest task (middleware implementation) — contains most logic
- FR-012 (no changes to exception handler) is validated by test in T010, not by implementation
- Spec explicitly requests tests (CLAUDE.md: "Every new function gets a test"), so test tasks are included
