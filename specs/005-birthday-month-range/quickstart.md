# Quickstart: Birthday Month Range Filter

## Prerequisites

- Python 3.14 with pyenv
- PostgreSQL running with test database
- `.env` configured at project root

## Validation Scenarios

### 1. Single month (backward compatibility)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/ipbcb/api/members/birthdays/?month=7"
```

**Expected**: 200 OK with `{"birthdays": [...]}` ordered by `birth_day` asc. Each entry includes `birth_month: 7`.

### 2. Month range

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/ipbcb/api/members/birthdays/?month=1-6"
```

**Expected**: 200 OK with birthdays from January through June, ordered by `birth_month` then `birth_day`.

### 3. Invalid range (start > end)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/ipbcb/api/members/birthdays/?month=6-1"
```

**Expected**: 400 with `{"month": ["Start month must be less than or equal to end month."]}`

### 4. Invalid format

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/ipbcb/api/members/birthdays/?month=abc"
```

**Expected**: 400 with `{"month": ["Month must be in format M or M-M (e.g., 7 or 1-6)."]}`

## Running Tests

```bash
export PATH="/home/node/.pyenv/versions/3.14.4/bin:$PATH"
cd /workspace/backend/server
pytest features/members/tests/ -v
```

All existing birthday tests must still pass. New tests cover range queries, validation errors, and ordering.

## Key Files Changed

See [plan.md](plan.md) — Source Code section for full file list.
