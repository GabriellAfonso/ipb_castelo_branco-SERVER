# Feature Specification: Structured JSON Logging

**Feature Branch**: `002-structured-json-logging`

**Created**: 2026-06-17

**Status**: Draft

**Input**: User description: "Add structured JSON logging to the Django API so every request and error is traceable in a Docker environment."

## User Scenarios & Testing

### User Story 1 - Trace an Error by Request ID (Priority: P1)

A developer investigates a bug reported by an Android user. The user provides the `X-Request-ID` header value from their failed request. The developer searches the Docker logs by that request ID and finds the complete request lifecycle: entry log, error details with traceback, and response status — all in a single JSON-queryable format.

**Why this priority**: Without request traceability, debugging production issues requires guessing which log lines belong to which request. This is the core value of the feature.

**Independent Test**: Can be tested by making an API call, capturing the `X-Request-ID` response header, and verifying that all log lines for that request share the same `request_id` field in JSON format.

**Acceptance Scenarios**:

1. **Given** a request to any API endpoint, **When** the response is returned, **Then** the response includes an `X-Request-ID` header containing a UUID4 value.
2. **Given** a request that triggers a 500 error, **When** the developer searches Docker logs for the `request_id`, **Then** they find both the request entry log and the error log with matching `request_id`, each as a valid JSON object.
3. **Given** a request to a protected endpoint without authentication, **When** the request fails with 401, **Then** the warning log emitted by the exception handler contains the `request_id` and is formatted as JSON.

---

### User Story 2 - Monitor Request Traffic in Docker (Priority: P2)

An operator views Docker container logs (`docker logs` or a future log collector) and sees structured JSON lines for every request. Each line includes method, path, status code, and duration, enabling filtering and aggregation without custom parsing.

**Why this priority**: Operational visibility is the second most valuable outcome — it enables monitoring, alerting, and performance analysis.

**Independent Test**: Can be tested by making several API calls and verifying that each produces a JSON log line at request completion containing `method`, `path`, `status_code`, and `duration_ms`.

**Acceptance Scenarios**:

1. **Given** a GET request to `/ipbcb/api/songs/`, **When** the request completes, **Then** stdout contains a JSON log line with fields: `timestamp`, `level`, `logger`, `message`, `request_id`, `method` ("GET"), `path` ("/ipbcb/api/songs/"), `status_code` (200), and `duration_ms` (a positive number).
2. **Given** an authenticated request, **When** the request is logged at entry, **Then** the JSON log line includes `user_id` with the authenticated user's ID.
3. **Given** an unauthenticated request, **When** the request is logged at entry, **Then** the `user_id` field is `null` or absent.

---

### User Story 3 - Existing Exception Logging Benefits Automatically (Priority: P3)

The existing `custom_exception_handler` already logs warnings and errors. After this feature is deployed, those log calls automatically output as structured JSON with request context — no changes needed to the exception handler code.

**Why this priority**: Ensures backward compatibility and validates that the logging configuration works transparently with existing code.

**Independent Test**: Can be tested by triggering a domain exception (e.g., NotFoundError) and verifying the resulting log line is valid JSON containing `request_id`, `level` ("WARNING"), and the error details.

**Acceptance Scenarios**:

1. **Given** a request that triggers a `NotFoundError`, **When** the exception handler logs a warning, **Then** the log output is a JSON object (not plain text) containing `request_id`, `level`, `logger`, and `message`.
2. **Given** a request that triggers an unhandled exception, **When** the exception handler logs an error with traceback, **Then** the traceback is included within the JSON structure (not as separate unstructured lines).

---

### Edge Cases

- What happens when a request is processed by middleware but never reaches a view (e.g., 404 from URL routing)? The middleware still logs request start and end with correct status code.
- What happens when the request body causes an exception during middleware processing? The middleware handles its own errors gracefully and still logs what it can.
- What happens when multiple concurrent requests are processed? Each request's logs contain its own unique `request_id` — no cross-contamination between threads.
- What happens when a log call occurs outside a request context (e.g., management command, startup)? The `request_id` field is absent or null — no errors raised.

## Requirements

### Functional Requirements

- **FR-001**: System MUST format all log output as structured JSON with fields: `timestamp` (ISO 8601), `level`, `logger`, and `message`.
- **FR-002**: System MUST write all logs to stdout via a single console handler, suitable for Docker log capture.
- **FR-003**: System MUST set the root logger to INFO level by default.
- **FR-004**: System MUST configure Django's built-in loggers (`django.request`, `django.server`, `django.db.backends`) at appropriate levels (WARNING for `django.server`, WARNING for `django.db.backends`).
- **FR-005**: System MUST generate a unique UUID4 `request_id` for every incoming HTTP request.
- **FR-006**: System MUST propagate `request_id` to all log records emitted during that request's lifecycle using `contextvars` or `threading.local`.
- **FR-007**: System MUST include `request_id` in every JSON log line emitted during a request context.
- **FR-008**: System MUST add the `request_id` as an `X-Request-ID` response header on every HTTP response.
- **FR-009**: System MUST log at request start: method, path, user_id (if authenticated), and client IP.
- **FR-010**: System MUST log at request end: method, path, status_code, and duration_ms.
- **FR-011**: System MUST allow callers to pass extra fields (e.g., `user_id`, `error_code`) that appear in the JSON output.
- **FR-012**: System MUST NOT modify the `custom_exception_handler` logic — it benefits from JSON formatting purely through the logging configuration.
- **FR-013**: Middleware MUST be placed in `core/http/` following existing project structure.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of log output from the application is valid JSON — parseable by standard JSON tools (`jq`, log collectors).
- **SC-002**: Any production error can be traced end-to-end using a single `request_id` value provided by the Android client from the `X-Request-ID` header.
- **SC-003**: Operators can determine request duration for any API call by reading the `duration_ms` field from the request-completion log line.
- **SC-004**: Zero changes required to existing logging call sites (`custom_exception_handler`, `google_auth_service`, schedule views) — they automatically produce JSON output.

## Assumptions

- The application runs in Docker, and Docker captures stdout/stderr — no file-based log handlers are needed.
- No external log collector (Loki, ELK) is in scope for this feature; JSON-to-stdout is sufficient for now.
- `python-json-logger` is the preferred library for JSON formatting (lightweight, well-maintained, stdlib-compatible). `structlog` is an acceptable alternative if the team prefers it.
- The Android client will store and surface the `X-Request-ID` header value for users to include in bug reports.
- Existing ad-hoc logging in `google_auth_service.py` and schedule views will not be refactored as part of this feature — they simply benefit from the new JSON formatter.
- The `request_id` is generated server-side; the client does not supply it (no `X-Request-ID` in the request).
- Performance overhead of request logging middleware is negligible for the expected traffic volume of an internal church app.
