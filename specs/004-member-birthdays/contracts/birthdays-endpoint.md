# API Contract: Member Birthdays Endpoint

## GET /api/members/birthdays/

Returns members whose birthday falls in the specified month.

### Authentication

Required. JWT Bearer token.

### Permissions

`IsAuthenticated` + `IsMemberUser`

### Query Parameters

| Parameter | Type | Required | Constraints | Description |
|-----------|------|----------|-------------|-------------|
| month | integer | Yes | 1-12 | Month number to filter birthdays |

### Success Response

**Status**: `200 OK`

```json
{
  "birthdays": [
    {
      "name": "Alice Johnson",
      "gender": "F",
      "birth_day": 5
    },
    {
      "name": "Bob Smith",
      "gender": "M",
      "birth_day": 18
    },
    {
      "name": "Carol Davis",
      "gender": null,
      "birth_day": 23
    }
  ]
}
```

**Ordering**: Results sorted by `birth_day` ascending.

**Empty result**: Returns `{"birthdays": []}` with status 200.

### Error Responses

#### 400 Bad Request — Missing month parameter

```json
{
  "month": ["This field is required."]
}
```

#### 400 Bad Request — Invalid month value

```json
{
  "month": ["Ensure this value is greater than or equal to 1."]
}
```

```json
{
  "month": ["Ensure this value is less than or equal to 12."]
}
```

```json
{
  "month": ["A valid integer is required."]
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
- Filter uses the month component of `birth_date` only (year is ignored)
