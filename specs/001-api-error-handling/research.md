# Research: API Error Handling

## R1: DRF Exception Handler Return Value for Unhandled Exceptions

**Decision**: Return a structured JSON 500 response instead of `None`.

**Rationale**: DRF's `exception_handler` returns `None` for non-DRF exceptions, which causes Django to fall back to its default error handling (HTML 500 page). Since the only client is an Android app expecting JSON, we must catch all unhandled exceptions and return a JSON response.

**Implementation**: After DRF's handler returns `None` and the exception is not a `DomainError`, wrap the exception in a generic 500 JSON response with `error_code: "INTERNAL_ERROR"`. Log the full traceback at ERROR level.

**Alternatives considered**:
- Django middleware for 500 handling — rejected because DRF's exception handler is the correct extension point and keeps all error logic in one place.
- Custom Django `handler500` — rejected because it only applies to non-DRF views.

## R2: Domain Exception `error_code` Attribute Design

**Decision**: Add `error_code` as a class attribute on `DomainError` base class. Each subclass overrides it.

**Rationale**: Class attribute is simple, static, and discoverable. No registry or mapping needed — the handler reads `exc.error_code` directly.

**Mapping**:
| Exception Class | error_code |
|----------------|------------|
| `DomainError` (base) | `"DOMAIN_ERROR"` |
| `NotFoundError` | `"NOT_FOUND"` |
| `ValidationError` | `"VALIDATION_ERROR"` |
| `ConflictError` | `"CONFLICT"` |
| `AuthenticationError` | `"AUTHENTICATION_FAILED"` |

Leaf exceptions (e.g., `BibleVersionNotFound`, `SongsNotFoundError`) inherit parent's `error_code` by default but can override if needed.

**Alternatives considered**:
- Separate error code registry/enum — rejected as over-engineering for ~10 exception classes.
- Error codes on instances, not classes — rejected because codes are stable per exception type, not per instance.

## R3: DRF ValidationError Conversion to Canonical Format

**Decision**: Intercept DRF's `ValidationError` in the handler and reshape `response.data` into canonical format.

**Rationale**: DRF serializer validation already returns field-level errors as `{"field": ["error1", "error2"]}`. We wrap this in `{"error_code": "VALIDATION_ERROR", "detail": "Validation failed.", "field_errors": {...}}`.

**Edge cases**:
- DRF `ValidationError` with a single string (non-field error): put in `detail`, no `field_errors`.
- DRF `ValidationError` with a list (non-field errors): join into `detail`.
- DRF `ValidationError` with a dict (field errors): move to `field_errors`, set generic `detail`.

**Alternatives considered**:
- Custom serializer base class that reformats errors — rejected because it doesn't catch all DRF validation paths (e.g., `ParseError`, permission checks).

## R4: Extra Context in Domain Exception Responses

**Decision**: Domain exceptions can define `extra_context()` method returning a dict. The handler merges this into the response body.

**Rationale**: Some exceptions carry domain-specific data (e.g., `SongsNotFoundError.missing_ids`). A generic mechanism avoids special-casing each exception in the handler.

**Implementation**: Base `DomainError.extra_context()` returns `{}`. Subclasses override to return relevant data. The handler calls `exc.extra_context()` and merges the result into the response dict.

**Alternatives considered**:
- Handler inspects exception attributes by name — rejected because it couples the handler to specific exception internals.
- Include all exception attributes automatically — rejected because some attributes are internal (e.g., `args`).

## R5: Logging Strategy

**Decision**: Use Python's `logging` module in the exception handler. WARNING for 4xx, ERROR with `exc_info=True` for 5xx.

**Rationale**: Structured logging with severity levels follows project convention (already used in `google_auth_service.py` and `schedule/views`). `exc_info=True` includes the full traceback for 5xx errors.

**Logger name**: `core.http.exceptions` (module-level logger).

**Alternatives considered**:
- Sentry integration — out of scope for this feature; can be added later by hooking into the same handler.
- Custom log format — unnecessary; project uses standard Python logging.

## R6: View Validation Migration Strategy

**Decision**: Move validation logic from views to services, using Pydantic DTOs for input validation.

**Views affected**:
1. `songs/views/register_plays.py` — date parsing, play item validation → service method or DTO
2. `songs/views/songs.py` — `_parse_fixed_param()` ValueError handling → service-level validation
3. `schedule/views/schedule.py` — KeyError/ValueError/TypeError catching → service-level validation
4. `accounts/views/auth.py` — Pydantic ValidationError catching → let it propagate as domain ValidationError

**Rationale**: Clean architecture mandates views only call services. Validation is business logic belonging in services.

**Alternatives considered**:
- DRF serializers for input validation — viable but project uses Pydantic DTOs, not serializers, for service input. Stay consistent.
