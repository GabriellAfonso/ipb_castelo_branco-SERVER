# Error Response Contract

All API error responses conform to this contract. The Android client can use a single parser for all errors.

## Schema

```json
{
  "error_code": "string (required, from Error Code Catalog)",
  "detail": "string (required, human-readable message)",
  "field_errors": "object (optional, field_name → string[])",
  "...extra_context": "any (optional, domain-specific keys)"
}
```

## Response Examples

### Not Found (404)

```json
{
  "error_code": "NOT_FOUND",
  "detail": "Lyrics not found: id=42"
}
```

### Validation Error — Field-Level (400)

```json
{
  "error_code": "VALIDATION_ERROR",
  "detail": "Validation failed.",
  "field_errors": {
    "date": ["Invalid date format. Use YYYY-MM-DD."],
    "plays": ["This field is required."]
  }
}
```

### Validation Error — Non-Field (400)

```json
{
  "error_code": "VALIDATION_ERROR",
  "detail": "Position must be between 1 and 4."
}
```

### Domain Error with Extra Context (404)

```json
{
  "error_code": "NOT_FOUND",
  "detail": "Some songs were not found: [5, 12]",
  "missing_song_ids": [5, 12]
}
```

### Authentication Failed (401)

```json
{
  "error_code": "AUTHENTICATION_FAILED",
  "detail": "Nome de usuario ou senha invalidos."
}
```

### Not Authenticated (401)

```json
{
  "error_code": "NOT_AUTHENTICATED",
  "detail": "Faca login para ter acesso."
}
```

### Permission Denied (403)

```json
{
  "error_code": "PERMISSION_DENIED",
  "detail": "Acesso restrito."
}
```

### Conflict (409)

```json
{
  "error_code": "CONFLICT",
  "detail": "Username already exists: 'joao123'"
}
```

### Throttled (429)

```json
{
  "error_code": "THROTTLED",
  "detail": "Request was throttled. Expected available in 30 seconds."
}
```

### Internal Error (500)

```json
{
  "error_code": "INTERNAL_ERROR",
  "detail": "An unexpected error occurred."
}
```

## Error Code Catalog

| error_code | HTTP Status | When |
|------------|-------------|------|
| `NOT_FOUND` | 404 | Resource does not exist |
| `VALIDATION_ERROR` | 400 | Input fails validation (domain or serializer) |
| `CONFLICT` | 409 | Operation conflicts with existing state |
| `AUTHENTICATION_FAILED` | 401 | Credentials invalid or token expired |
| `NOT_AUTHENTICATED` | 401 | No credentials provided |
| `PERMISSION_DENIED` | 403 | Authenticated but insufficient permissions |
| `THROTTLED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Unhandled server error |
| `DOMAIN_ERROR` | 500 | Generic domain error (fallback) |

## Guarantees

1. `error_code` and `detail` are always present on every error response.
2. `field_errors` is only present when the error is a validation error with field-level detail.
3. Extra context keys (e.g., `missing_song_ids`) are only present when the domain exception provides them.
4. `error_code` values are stable strings — they will not change without a versioned migration.
5. `detail` is human-readable and may be in Portuguese. Do not parse it programmatically — use `error_code` instead.
