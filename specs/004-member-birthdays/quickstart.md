# Quickstart: Member Birthdays Endpoint

## Prerequisites

- Python virtual environment activated (wsl_venv)
- PostgreSQL running with dev database
- Test fixtures or existing Member records with `birth_date` set

## Validation Scenarios

### 1. Run unit tests

```bash
source wsl_venv/bin/activate
cd server && python -m pytest features/members/tests/unit/test_member_service.py -v
```

**Expected**: All service-layer tests pass (filtering by month, ordering by day, null exclusion).

### 2. Run integration tests

```bash
source wsl_venv/bin/activate
cd server && python -m pytest features/members/tests/integration/test_birthdays_api.py -v
```

**Expected**: All endpoint tests pass:
- 200 with valid month and matching members
- 200 with empty list when no matches
- 400 when month missing, invalid, or out of range
- 401 when unauthenticated
- 403 when authenticated but not member user

### 3. Manual validation (dev server)

```bash
source wsl_venv/bin/activate
cd server && python manage.py runserver
```

```bash
# Get auth token first
TOKEN="<your-jwt-token>"

# Valid request
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/members/birthdays/?month=7"

# Missing month (expect 400)
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/members/birthdays/"

# Invalid month (expect 400)
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/members/birthdays/?month=13"

# No auth (expect 401)
curl "http://localhost:8000/api/members/birthdays/?month=7"
```

**Expected responses**: See [contracts/birthdays-endpoint.md](contracts/birthdays-endpoint.md) for exact response shapes.

### 4. Verify OpenAPI schema

```bash
curl http://localhost:8000/api/schema/ | python -m json.tool | grep birthdays
```

**Expected**: Endpoint appears in the schema with `month` query parameter documented.
