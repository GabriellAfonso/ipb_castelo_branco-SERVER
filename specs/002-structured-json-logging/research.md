# Research: Structured JSON Logging

## Decision 1: JSON Logging Library

**Decision**: Use `python-json-logger` (package `python-json-logger>=3.0,<4.0`)

**Rationale**:
- Lightweight — single-purpose library, no extra abstractions
- Works directly with Python's stdlib `logging` module — drop-in formatter replacement
- Django's `LOGGING` dictConfig integrates seamlessly with custom formatters
- Well-maintained, widely adopted (10M+ monthly downloads)
- v3.x supports Python 3.12+ with modern typing

**Alternatives considered**:
- `structlog`: More powerful (processors, bound loggers), but heavier. Overkill for this use case — we only need JSON formatting, not a new logging paradigm. Better fit if we later need structured context binding across deep call stacks.
- Manual `json.dumps` in a custom formatter: Works but reinvents what `python-json-logger` already does (timestamp formatting, exception serialization, extra fields). Not worth the maintenance.

## Decision 2: Request ID Propagation Mechanism

**Decision**: Use `contextvars.ContextVar` with a custom `logging.Filter`

**Rationale**:
- `contextvars` is stdlib (Python 3.7+), thread-safe, and async-safe
- Works correctly with Django's sync views and any future async views
- A `logging.Filter` attached to the handler injects `request_id` into every log record automatically — existing `logger.warning()` calls in `custom_exception_handler` get `request_id` without code changes
- No need for `threading.local` — `contextvars` supersedes it

**Alternatives considered**:
- `threading.local`: Works for sync Django but breaks with async views. `contextvars` handles both.
- Middleware-injected `request.META` attribute: Requires passing `request` everywhere — violates clean architecture (services don't know HTTP objects).

## Decision 3: Middleware Position

**Decision**: Insert `RequestLoggingMiddleware` as the second middleware (after `SecurityMiddleware`, before `SessionMiddleware`)

**Rationale**:
- Must be early to capture full request duration including other middleware processing
- `SecurityMiddleware` should stay first (handles SSL redirect, HSTS)
- Being before `AuthenticationMiddleware` means `user_id` is not yet available at request start — solve by reading `request.user` at response time (after auth middleware has run) and logging it in the completion log

## Decision 4: Client IP Extraction

**Decision**: Read from `HTTP_X_FORWARDED_FOR` (first IP) with fallback to `REMOTE_ADDR`

**Rationale**:
- App runs behind nginx — real client IP is in `X-Forwarded-For`
- First IP in the chain is the client; subsequent are proxies
- Fallback to `REMOTE_ADDR` for direct connections (dev environment)

## Decision 5: Log Level Strategy

**Decision**:
- Root logger: `INFO`
- `django.request`: `WARNING` (Django logs 4xx/5xx here; our exception handler already covers these)
- `django.server`: `WARNING` (noisy at INFO — logs every request in dev server)
- `django.db.backends`: `WARNING` (SQL queries at DEBUG — only enable explicitly for debugging)

**Rationale**:
- INFO on root captures our middleware logs and application logs
- Suppressing Django's built-in request/server loggers avoids duplicate request logging (our middleware handles this)
- DB query logging stays off by default to avoid massive log volume
