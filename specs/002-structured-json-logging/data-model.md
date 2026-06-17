# Data Model: Structured JSON Logging

This feature introduces no database entities. All data is transient (log records and request context).

## Transient Data Structures

### JSON Log Record

Every log line emitted by the application. Not persisted in DB — written to stdout.

| Field | Type | Required | Source |
|-------|------|----------|--------|
| `timestamp` | string (ISO 8601) | yes | Formatter |
| `level` | string (DEBUG/INFO/WARNING/ERROR/CRITICAL) | yes | Formatter |
| `logger` | string | yes | Formatter (`name` attribute) |
| `message` | string | yes | Formatter |
| `request_id` | string (UUID4) or null | no | Filter (from contextvars) |
| `exc_info` | string or null | no | Formatter (traceback if present) |
| `*` (extra fields) | any | no | Caller-provided extras (e.g., `user_id`, `error_code`, `method`, `path`) |

### Request Context (ContextVar)

Held in `contextvars.ContextVar` for the duration of a single request.

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | string (UUID4) | Unique identifier for this request |

### Request Start Log (extra fields)

| Field | Type | Description |
|-------|------|-------------|
| `method` | string | HTTP method (GET, POST, etc.) |
| `path` | string | Request path |
| `user_id` | int or null | Authenticated user ID (null if anonymous) |
| `client_ip` | string | Client IP address |

### Request End Log (extra fields)

| Field | Type | Description |
|-------|------|-------------|
| `method` | string | HTTP method |
| `path` | string | Request path |
| `status_code` | int | HTTP response status code |
| `duration_ms` | float | Request processing time in milliseconds |
| `user_id` | int or null | Authenticated user ID |
