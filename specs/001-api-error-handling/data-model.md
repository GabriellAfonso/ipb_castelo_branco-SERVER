# Data Model: API Error Handling

No database entities are introduced by this feature. All changes are in-memory exception classes and response formatting.

## Domain Exception Hierarchy

```
DomainError (error_code="DOMAIN_ERROR")
├── NotFoundError (error_code="NOT_FOUND")
│   ├── BibleVersionNotFound
│   ├── ChordChartNotFoundError
│   ├── LyricsNotFoundError
│   ├── ProfileNotFoundError
│   └── SongsNotFoundError        ← moved from register_plays_service.py
├── ValidationError (error_code="VALIDATION_ERROR")
│   └── UnverifiedGoogleEmailError
├── ConflictError (error_code="CONFLICT")
│   └── UsernameAlreadyExistsError
├── AuthenticationError (error_code="AUTHENTICATION_FAILED")
│   ├── InvalidCredentialsError
│   └── InvalidGoogleTokenError
└── GoogleUserCreationError (error_code="DOMAIN_ERROR")
```

## Exception Class Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `error_code` | `str` (class attr) | Machine-readable error code. Inherited from parent unless overridden. |
| `message` | `str` | Human-readable detail. Passed to `Exception.__init__()`. |
| `extra_context()` | `dict` (method) | Returns additional domain data for the response. Default: `{}`. |

## Canonical Error Response Shape

```json
{
  "error_code": "NOT_FOUND",
  "detail": "Lyrics not found: id=42",
  "field_errors": {
    "song_id": ["This field is required."],
    "position": ["Must be between 1 and 10."]
  }
}
```

| Field | Type | Present | Description |
|-------|------|---------|-------------|
| `error_code` | `string` | Always | Machine-readable error code |
| `detail` | `string` | Always | Human-readable error description |
| `field_errors` | `object` | Only for validation errors | Maps field names to lists of error strings |
| *(extra context)* | varies | Only when exception provides it | Domain-specific data (e.g., `missing_song_ids`) |

## Error Code Catalog

| error_code | HTTP Status | Source |
|------------|-------------|--------|
| `NOT_FOUND` | 404 | `NotFoundError` subclasses |
| `VALIDATION_ERROR` | 400 | `ValidationError` subclasses, DRF serializer errors |
| `CONFLICT` | 409 | `ConflictError` subclasses |
| `AUTHENTICATION_FAILED` | 401 | `AuthenticationError` subclasses, DRF `AuthenticationFailed` |
| `NOT_AUTHENTICATED` | 401 | DRF `NotAuthenticated` |
| `PERMISSION_DENIED` | 403 | DRF `PermissionDenied` |
| `THROTTLED` | 429 | DRF `Throttled` |
| `INTERNAL_ERROR` | 500 | Unhandled exceptions |
| `DOMAIN_ERROR` | 500 | Generic `DomainError` (fallback) |
