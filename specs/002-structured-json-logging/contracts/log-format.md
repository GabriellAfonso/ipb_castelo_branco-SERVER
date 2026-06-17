# Contract: JSON Log Line Format

All log output from the application MUST be a single-line JSON object written to stdout.

## Base Fields (every log line)

```json
{
  "timestamp": "2026-06-17T14:30:00.123456-03:00",
  "level": "INFO",
  "logger": "core.http.middleware.request_logging",
  "message": "Request started"
}
```

## With Request Context (during HTTP request lifecycle)

```json
{
  "timestamp": "2026-06-17T14:30:00.123456-03:00",
  "level": "INFO",
  "logger": "core.http.middleware.request_logging",
  "message": "Request started",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## Request Start Log

```json
{
  "timestamp": "2026-06-17T14:30:00.123456-03:00",
  "level": "INFO",
  "logger": "core.http.middleware.request_logging",
  "message": "Request started",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "GET",
  "path": "/ipbcb/api/songs/",
  "user_id": null,
  "client_ip": "192.168.1.100"
}
```

## Request End Log

```json
{
  "timestamp": "2026-06-17T14:30:00.456789-03:00",
  "level": "INFO",
  "logger": "core.http.middleware.request_logging",
  "message": "Request completed",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "GET",
  "path": "/ipbcb/api/songs/",
  "status_code": 200,
  "duration_ms": 42.3,
  "user_id": 15
}
```

## Exception Handler Log (existing, now JSON-formatted)

```json
{
  "timestamp": "2026-06-17T14:30:00.456789-03:00",
  "level": "WARNING",
  "logger": "core.http.exceptions",
  "message": "Client error 404 NOT_FOUND: Song not found: id=99",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## Error with Traceback

```json
{
  "timestamp": "2026-06-17T14:30:00.456789-03:00",
  "level": "ERROR",
  "logger": "core.http.exceptions",
  "message": "Server error INTERNAL_ERROR: division by zero",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "exc_info": "Traceback (most recent call last):\n  File \"...\"\nZeroDivisionError: division by zero"
}
```

## Response Header Contract

Every HTTP response includes:

```
X-Request-ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

Value matches the `request_id` field in all log lines emitted during that request.
