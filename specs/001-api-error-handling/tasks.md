# Tasks: API Error Handling

**Input**: Design documents from `specs/001-api-error-handling/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project setup needed — existing project. Skip to Foundational.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain exception hierarchy with `error_code` and `extra_context()` — MUST complete before handler or view changes.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 Add `error_code` class attribute and `extra_context()` method to `DomainError` base class and all intermediate exception classes (`NotFoundError`, `ValidationError`, `ConflictError`, `AuthenticationError`) in `server/core/domain/exceptions.py`. Mapping: `DomainError="DOMAIN_ERROR"`, `NotFoundError="NOT_FOUND"`, `ValidationError="VALIDATION_ERROR"`, `ConflictError="CONFLICT"`, `AuthenticationError="AUTHENTICATION_FAILED"`. Base `extra_context()` returns `{}`.
- [x] T002 Move `SongsNotFoundError` from `server/features/songs/services/register_plays_service.py` to `server/core/domain/exceptions.py`. Add `extra_context()` method returning `{"missing_song_ids": self.missing_ids}`. Update the import in `register_plays_service.py` to point to the new location.
- [x] T003 Update all other leaf exception classes in `server/core/domain/exceptions.py` to ensure they inherit `error_code` from their parent (no action needed if already inheriting) and add `extra_context()` overrides where relevant (e.g., `BibleVersionNotFound` → `{"version": self.version}`, `ProfileNotFoundError` → `{"user_id": self.user_id}`).

**Checkpoint**: All domain exceptions have `error_code` attribute and `extra_context()` method. `SongsNotFoundError` consolidated.

---

## Phase 3: User Story 1+2 - Consistent Format & Error Codes (Priority: P1) MVP

**Goal**: Centralized handler produces canonical `{"error_code", "detail", "field_errors?"}` format for ALL exception types — domain, DRF, and unhandled.

**Independent Test**: Trigger errors across all categories (404, 400, 401, 403, 409, 429, 500) and verify every response matches canonical format with correct `error_code`.

US1 and US2 are inseparable — canonical format inherently includes `error_code`. Combined into one phase.

### Implementation

- [x] T004 [US1] Rewrite `custom_exception_handler` in `server/core/http/exceptions.py`: handle `DomainError` subclasses by reading `exc.error_code`, `str(exc)` as detail, and `exc.extra_context()` as extra keys. Map exception types to HTTP status codes (same mapping as current). Build response as `{"error_code": ..., "detail": ..., **extra_context}`.
- [x] T005 [US1] In `custom_exception_handler` in `server/core/http/exceptions.py`: after DRF's `exception_handler` processes a DRF exception, reshape `response.data` into canonical format. Handle `DRF ValidationError` (dict → `field_errors` + generic detail; list → joined detail; string → detail). Handle `NotAuthenticated` → `error_code="NOT_AUTHENTICATED"`, `AuthenticationFailed` → `error_code="AUTHENTICATION_FAILED"`, `PermissionDenied` → `error_code="PERMISSION_DENIED"`, `Throttled` → `error_code="THROTTLED"`. Preserve existing Portuguese detail messages.
- [x] T006 [US1] In `custom_exception_handler` in `server/core/http/exceptions.py`: when DRF handler returns `None` and exception is not `DomainError`, return structured 500 response `{"error_code": "INTERNAL_ERROR", "detail": "An unexpected error occurred."}`. In DEBUG mode, include exception message in detail.
- [x] T007 [US1] Update existing tests in `server/core/tests/unit/test_exception_handler.py` to assert canonical format (`error_code` + `detail` keys) for all tested scenarios. Add new test cases: domain exceptions with `extra_context`, DRF `ValidationError` with field errors (dict), DRF `ValidationError` with non-field errors (list/string), `Throttled`, unhandled exception returning JSON 500, DEBUG mode 500 with exception message.

**Checkpoint**: Handler produces canonical format for every exception type. All error codes documented in contract are returned correctly.

---

## Phase 4: User Story 3 - Centralized Error Processing (Priority: P2)

**Goal**: Remove all manual try/except from views. Validation moves to services. Views only call services and return responses.

**Independent Test**: Trigger all previously manually-caught errors and verify centralized handler returns correct responses.

### Implementation

- [x] T008 [US3] Remove try/except for `BibleVersionNotFound` in `server/features/bible/views/__init__.py`. Let exception bubble to centralized handler (already returns 404 via handler).
- [x] T009 [US3] Remove try/except for `InvalidCredentialsError` and Pydantic `ValidationError` in `server/features/accounts/views/auth.py`. For Pydantic `ValidationError`: convert to domain `ValidationError` in the service layer (`server/features/accounts/services/auth_service.py`) or let the centralized handler catch Pydantic errors and map them to canonical format.
- [x] T010 [US3] Move date parsing and play item validation from `server/features/songs/views/register_plays.py` into the service layer. Create or update a Pydantic DTO for register plays input in `server/core/application/dtos/` (or existing DTO location). The service in `server/features/songs/services/register_plays_service.py` should validate input and raise domain `ValidationError` on failure. Remove all try/except from the view — it should only call the service and return the response.
- [x] T011 [US3] Reviewed `_parse_fixed_param()` in `server/features/songs/views/songs.py` — no change needed. Function is best-effort input parsing that silently skips invalid entries, not error-formatting logic. `raise ValidationError(...)` calls in songs views already use domain exceptions that bubble to centralized handler correctly.
- [x] T012 [US3] Remove try/except blocks from `server/features/schedule/views/schedule.py`. Move `KeyError`/`ValueError`/`TypeError` validation into the schedule service (`server/features/schedule/services/monthly_scheduler.py` or equivalent). Service raises domain `ValidationError` instead of letting raw Python exceptions escape. Remove the manual `{"error": str(e)}` response pattern.
- [x] T013 [US3] Handle Pydantic `ValidationError` (from `pydantic`) in the centralized handler (`server/core/http/exceptions.py`). When a Pydantic `ValidationError` reaches the handler (not caught by service), map it to canonical format: `error_code="VALIDATION_ERROR"`, extract field errors from `exc.errors()` into `field_errors`, set appropriate detail message. This serves as a safety net for any Pydantic validation that slips through services.

**Checkpoint**: Zero view files contain try/except for error formatting. All validation lives in services.

---

## Phase 5: User Story 4 - Error Logging (Priority: P2)

**Goal**: Every error processed by the handler is logged — WARNING for 4xx, ERROR with traceback for 5xx.

**Independent Test**: Trigger 4xx and 5xx errors, verify log output with correct severity and content.

### Implementation

- [x] T014 [US4] Add module-level logger (`logger = logging.getLogger("core.http.exceptions")`) to `server/core/http/exceptions.py`. In the handler: after building the response, log at WARNING level for 4xx (include error_code, detail, request path) and ERROR level with `exc_info=True` for 5xx (include full traceback).
- [x] T015 [US4] Remove manual `logger.exception()` calls from `server/features/schedule/views/schedule.py` that are now redundant (handler logs instead). Keep `logger.warning()` in `server/features/accounts/services/google_auth_service.py` `_sync_profile_photo` — that's intentional non-error logging for a non-critical operation.
- [x] T016 [US4] Add logging tests in `server/core/tests/unit/test_exception_handler.py`: verify WARNING log emitted for 4xx domain errors, verify ERROR log with traceback for unhandled 500, verify ERROR log for domain 500 (generic `DomainError`).

**Checkpoint**: All errors logged. 5xx errors include tracebacks for debugging.

---

## Phase 6: User Story 5 - Exception Consolidation (Priority: P3)

**Goal**: All domain exceptions in one file with `error_code` attributes. No scattered definitions.

**Independent Test**: `grep -rn "class.*DomainError\|class.*NotFoundError" server/ --include="*.py"` returns only `core/domain/exceptions.py` hits.

### Implementation

- [x] T017 [US5] Verify all domain exception subclasses are in `server/core/domain/exceptions.py` (T002 already moved `SongsNotFoundError`). Run grep to confirm no other domain exceptions exist outside this file. If any found, move them.
- [x] T018 [US5] Verify every exception class in `server/core/domain/exceptions.py` has `error_code` inherited or explicitly set (T001/T003 already did this). Add a simple unit test in `server/core/tests/unit/test_exception_handler.py` that imports all domain exception classes and asserts each has a non-empty `error_code` attribute.

**Checkpoint**: SC-004 (zero scattered exceptions) and SC-006 (all have error_code) verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [x] T019 Run full quickstart.md validation scenarios from `specs/001-api-error-handling/quickstart.md` — all 6 validation checks must pass.
- [x] T020 Update `specs/001-api-error-handling/spec.md` status from "Draft" to "Implemented". Update any acceptance scenarios that changed during implementation.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately
- **US1+2 (Phase 3)**: Depends on Phase 2 (needs `error_code` on exceptions)
- **US3 (Phase 4)**: Depends on Phase 3 (handler must be ready before removing view try/except)
- **US4 (Phase 5)**: Depends on Phase 3 (logging goes into the new handler)
- **US5 (Phase 6)**: Depends on Phase 2 (T002 already done), Phase 4 (scattered exceptions moved)
- **Polish (Phase 7)**: Depends on all previous phases

### User Story Dependencies

- **US1+2 (P1)**: Start after Phase 2. No dependencies on other stories.
- **US3 (P2)**: Start after Phase 3. Needs handler working before removing view try/except.
- **US4 (P2)**: Can start after Phase 3. Independent of US3 — can run in parallel with US3.
- **US5 (P3)**: Can start after Phase 4. Verification/cleanup phase.

### Within Each Phase

- T004 → T005 → T006 (sequential — same file, incremental handler changes)
- T007 after T004-T006 (tests for completed handler)
- T008, T009, T010, T011, T012 can run in parallel (different view files)
- T013 after T004-T006 (extends handler)
- T014 after T004-T006 (extends handler)

### Parallel Opportunities

```text
# After Phase 3 completes, these can run in parallel:
Phase 4 (US3): T008 || T009 || T010 || T011 || T012  (different view files)
Phase 5 (US4): T014  (different concern — logging)

# Within Phase 2:
T001 → T002, T003 (T002/T003 parallel after T001)
```

---

## Implementation Strategy

### MVP First (Phase 2 + Phase 3)

1. Complete Phase 2: Add `error_code` + `extra_context()` to domain exceptions
2. Complete Phase 3: Rewrite centralized handler with canonical format
3. **STOP and VALIDATE**: Test all error codes against contract
4. This alone delivers SC-001, SC-002, SC-006

### Incremental Delivery

1. Phase 2 + Phase 3 → Canonical format works (MVP)
2. Phase 4 → Views cleaned up (SC-005)
3. Phase 5 → Logging added (SC-003)
4. Phase 6 → Consolidation verified (SC-004)
5. Phase 7 → Full validation pass

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US2 combined — inseparable (format includes error codes)
- US3 and US4 can run in parallel after Phase 3
- Commit after each task or logical group
- gallery/views/upload.py is out of scope (HTML endpoint)
- google_auth_service.py `_sync_profile_photo` logging stays as-is (intentional)
