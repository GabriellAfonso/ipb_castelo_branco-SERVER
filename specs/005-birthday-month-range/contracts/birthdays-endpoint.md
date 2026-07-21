# API Contract: Member Birthdays Endpoint (Updated)

## GET /api/members/birthdays/

Returns members whose birthday falls in the specified month or month range.

### Authentication

Required. JWT Bearer token.

### Permissions

`IsAuthenticated` + `IsMemberUser`

### Query Parameters

| Parameter | Type | Required | Format | Description |
|-----------|------|----------|--------|-------------|
| month | string | Yes | `M` or `M-M` | Single month (1-12) or range (e.g., 1-6). Both values must be integers 1-12, start <= end. |

**Examples**:
- `?month=7` — birthdays in July
- `?month=1-6` — birthdays from January through June
- `?month=12-12` — equivalent to `?month=12`

### Success Response

**Status**: `200 OK`

#### Single month example (`?month=7`)

```json
{
  "birthdays": [
    {
      "name": "Alice Johnson",
      "gender": "F",
      "birth_month": 7,
      "birth_day": 5
    },
    {
      "name": "Bob Smith",
      "gender": "M",
      "birth_month": 7,
      "birth_day": 18
    }
  ]
}
```

#### Range example (`?month=1-3`)

```json
{
  "birthdays": [
    {
      "name": "Carol Davis",
      "gender": null,
      "birth_month": 1,
      "birth_day": 10
    },
    {
      "name": "Alice Johnson",
      "gender": "F",
      "birth_month": 2,
      "birth_day": 5
    },
    {
      "name": "Bob Smith",
      "gender": "M",
      "birth_month": 3,
      "birth_day": 18
    }
  ]
}
```

**Ordering**:
- Range: sorted by `birth_month` ascending, then `birth_day` ascending
- Single month: sorted by `birth_day` ascending (month is constant)

**Empty result**: Returns `{"birthdays": []}` with status 200.

### Error Responses

#### 400 Bad Request — Missing month parameter

```json
{
  "month": ["This field is required."]
}
```

#### 400 Bad Request — Invalid format

```json
{
  "month": ["Month must be in format M or M-M (e.g., 7 or 1-6)."]
}
```

#### 400 Bad Request — Out of range

```json
{
  "month": ["Month values must be between 1 and 12."]
}
```

#### 400 Bad Request — Start greater than end

```json
{
  "month": ["Start month must be less than or equal to end month."]
}
```

#### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### 403 Forbidden

```json
{
  "detail": "Disponivel apenas para membros."
}
```

### Filtering Rules

- Only active members (`is_active=True`) are included
- Members with `birth_date=NULL` are excluded
- Filter uses the month component of `birth_date` (year is ignored)
- Range is inclusive on both ends

### Backward Compatibility

- Single month format (`?month=7`) produces identical results to previous version, with the addition of the `birth_month` field
- New `birth_month` field is additive — existing clients can safely ignore it
