# Feature Specification: API Error Handling

**Feature Branch**: `001-api-error-handling`

**Created**: 2026-06-16

**Status**: Implemented

**Input**: Improve the API exception handling system to make errors consistent, traceable, and actionable for the Android client.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Error Responses (Priority: P1)

As the Android client developer, I receive a single predictable JSON format for every API error so I can write one error-handling path instead of branching on multiple response shapes.

**Why this priority**: The inconsistency between `{"error": ...}` and `{"detail": ...}` is the root cause of duplicated client-side logic and missed error cases. Fixing this unlocks all other improvements.

**Independent Test**: Send requests that trigger validation errors, not-found errors, authentication failures, and server errors across different endpoints. Every response must match the canonical format.

**Acceptance Scenarios**:

1. **Given** any API endpoint, **When** any error occurs, **Then** the response body contains exactly `{"error_code": "<CODE>", "detail": "<message>"}` with an optional `"field_errors"` key for validation errors.
2. **Given** a validation error with field-level details, **When** the error is returned, **Then** the response includes `"field_errors": {"field_name": ["error message"]}` alongside `error_code` and `detail`.
3. **Given** an endpoint that previously returned `{"error": "..."}`, **When** the same error occurs, **Then** the response now uses the canonical format with `error_code` and `detail`.

---

### User Story 2 - Machine-Readable Error Codes (Priority: P1)

As the Android client, I receive a stable `error_code` string (e.g., `"NOT_FOUND"`, `"VALIDATION_ERROR"`) so I can programmatically react to specific error types without parsing human-readable messages.

**Why this priority**: Without machine-readable codes, the client must match on localized Portuguese strings, which is fragile and breaks on any wording change.

**Independent Test**: Trigger each category of error and verify the `error_code` value is a documented, stable string.

**Acceptance Scenarios**:

1. **Given** a resource that does not exist, **When** I request it, **Then** the response contains `"error_code": "NOT_FOUND"`.
2. **Given** invalid input data, **When** I submit it, **Then** the response contains `"error_code": "VALIDATION_ERROR"`.
3. **Given** an expired or missing token, **When** I call a protected endpoint, **Then** the response contains `"error_code": "AUTHENTICATION_FAILED"` or `"NOT_AUTHENTICATED"`.
4. **Given** a duplicate resource conflict, **When** I attempt the operation, **Then** the response contains `"error_code": "CONFLICT"`.
5. **Given** an unhandled server error, **When** it occurs, **Then** the response contains `"error_code": "INTERNAL_ERROR"`.
6. **Given** insufficient permissions, **When** I call a restricted endpoint, **Then** the response contains `"error_code": "PERMISSION_DENIED"`.
7. **Given** a request is throttled, **When** rate limit is exceeded, **Then** the response contains `"error_code": "THROTTLED"`.

---

### User Story 3 - Centralized Error Processing (Priority: P2)

As a backend developer, all errors flow through a single centralized handler so that logging, formatting, and future tracing happen in one place — no manual try/except in views.

**Why this priority**: Manual exception handling in views bypasses logging and formatting. Centralizing is the enabler for consistent format and observability.

**Independent Test**: Remove all manual try/except blocks from views, trigger the same errors, and verify they still produce correct responses via the centralized handler.

**Acceptance Scenarios**:

1. **Given** any view endpoint, **When** a domain exception is raised in the service layer, **Then** the centralized handler catches it and returns the correct response — the view has no try/except for it.
2. **Given** a view that previously caught `SongsNotFoundError` manually, **When** the same error occurs, **Then** the centralized handler produces the same HTTP status and includes `missing_song_ids` in the response.
3. **Given** input validation that previously happened in a view, **When** invalid input is sent, **Then** validation happens in the service layer and the resulting domain exception flows to the centralized handler. Exception: best-effort input parsing that silently skips malformed entries (e.g., `_parse_fixed_param`, preview fixed-list parsing) may remain in views since it does not produce error responses.

---

### User Story 4 - Error Logging and Traceability (Priority: P2)

As a backend developer, every error is logged with appropriate severity so that 500 errors are traceable and 4xx patterns are observable.

**Why this priority**: Currently 500 errors disappear silently. Logging is essential for debugging production issues.

**Independent Test**: Trigger 4xx and 5xx errors, then verify log output contains the expected severity level and details.

**Acceptance Scenarios**:

1. **Given** a 4xx error occurs, **When** the centralized handler processes it, **Then** a WARNING-level log entry is created with the error code and detail.
2. **Given** a 5xx error occurs, **When** the centralized handler processes it, **Then** an ERROR-level log entry is created with the full traceback.
3. **Given** an unhandled exception (not a DomainError or DRF exception), **When** it reaches the handler, **Then** an ERROR-level log with traceback is created and a structured 500 JSON response is returned (not Django's HTML error page).

---

### User Story 5 - Domain Exception Consolidation (Priority: P3)

As a backend developer, all domain exceptions live in `core/domain/exceptions.py` with a default `error_code` attribute, so the exception hierarchy is discoverable and consistent.

**Why this priority**: Scattered exception definitions (e.g., `SongsNotFoundError` in a service file) make the system harder to understand and maintain. Lower priority because it's a code organization improvement.

**Independent Test**: Verify no domain exception subclass exists outside `core/domain/exceptions.py`. Verify every domain exception has an `error_code` attribute.

**Acceptance Scenarios**:

1. **Given** the codebase, **When** I search for classes inheriting from `DomainError`, **Then** all are defined in `core/domain/exceptions.py`.
2. **Given** any domain exception class, **When** I inspect it, **Then** it has an `error_code` class attribute (e.g., `"NOT_FOUND"`, `"CONFLICT"`).
3. **Given** `SongsNotFoundError`, **When** I look for its definition, **Then** it is in `core/domain/exceptions.py` alongside other domain exceptions, with relevant attributes like `missing_ids`.

---

### Edge Cases

- What happens when a DRF serializer raises its own `ValidationError`? The handler must convert it to the canonical format with `field_errors`.
- What happens when an unhandled exception type (e.g., `RuntimeError`, `OSError`) reaches the handler? It must return a structured 500 JSON response, never Django's HTML error page.
- What happens when a domain exception carries extra context (e.g., `missing_song_ids`)? The handler must include that context in the response body.
- What happens when multiple field errors exist on the same field? `field_errors` must support a list of messages per field.
- What happens in DEBUG mode? Unhandled 500 errors MUST include the exception message in detail for developer convenience, but never a traceback in the response body.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST return all error responses in the canonical format: `{"error_code": "<CODE>", "detail": "<message>"}` with an optional `"field_errors"` object for validation errors.
- **FR-002**: System MUST assign a stable, machine-readable `error_code` string to every error response. Codes include at minimum: `NOT_FOUND`, `VALIDATION_ERROR`, `CONFLICT`, `AUTHENTICATION_FAILED`, `NOT_AUTHENTICATED`, `PERMISSION_DENIED`, `THROTTLED`, `INTERNAL_ERROR`.
- **FR-003**: Every domain exception class MUST have a default `error_code` class attribute that maps to the corresponding code.
- **FR-004**: The centralized exception handler MUST process all domain exceptions (`DomainError` subclasses), DRF exceptions, and unhandled exceptions — views MUST NOT contain try/except blocks for error formatting.
- **FR-005**: The handler MUST log 4xx errors at WARNING level and 5xx errors at ERROR level with full traceback.
- **FR-006**: Unhandled exceptions (non-domain, non-DRF) MUST return a structured JSON 500 response, never Django's default HTML error page or `None`.
- **FR-007**: DRF serializer `ValidationError` responses MUST be converted to the canonical format, mapping field-level errors to the `field_errors` key.
- **FR-008**: All domain exception classes MUST be defined in `core/domain/exceptions.py` — no domain exceptions scattered in service or view files.
- **FR-009**: Domain exceptions that carry extra context (e.g., `SongsNotFoundError.missing_ids`) MUST have that context included in the error response body as additional keys.
- **FR-010**: The existing domain exception hierarchy (`DomainError` -> `NotFoundError`, `ValidationError`, `ConflictError`, `AuthenticationError`) MUST be preserved.
- **FR-011**: Views MUST only call services and return responses — validation logic that currently lives in views MUST move to the service layer.

### Key Entities

- **DomainError**: Base exception class. Carries `error_code` (string) and `detail` (string). Parent of all domain-specific exceptions.
- **Error Response**: Canonical JSON shape returned to the client: `error_code`, `detail`, and optionally `field_errors` (dict of field name to list of error strings).
- **Centralized Exception Handler**: Single function registered with DRF that processes all exceptions into the canonical response format.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of API error responses across all endpoints conform to the canonical JSON format — zero endpoints return the old `{"error": ...}` shape.
- **SC-002**: The Android client can handle all errors with a single response parser that reads `error_code`, `detail`, and optionally `field_errors`.
- **SC-003**: Every 5xx error produces a log entry with full traceback, enabling root-cause analysis without reproducing the issue.
- **SC-004**: Zero domain exception classes exist outside `core/domain/exceptions.py`.
- **SC-005**: Zero view files contain try/except blocks for error response formatting.
- **SC-006**: Every domain exception class has an `error_code` attribute that matches one of the documented error codes.

## Assumptions

- The Android client will be updated to consume the new canonical error format. A transition period is not required since this is an internal app with a single client under our control.
- Existing Portuguese user-facing messages in `detail` fields will be preserved — the `error_code` is for programmatic use, `detail` remains human-readable.
- The `_sync_profile_photo` silent failure pattern in `google_auth_service.py` is intentional (non-critical operation) and will remain as-is — it does not need to flow through the centralized handler.
- Validation logic moving from views to services may require new or updated DTOs (Pydantic models) to carry the input data.
- The `gallery/views/upload.py` HTML error response is a special case (non-API endpoint) and is out of scope for this feature — only JSON API endpoints are covered.
