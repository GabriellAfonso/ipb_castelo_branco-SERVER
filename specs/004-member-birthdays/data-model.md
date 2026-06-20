# Data Model: Member Birthdays Endpoint

## Existing Entities (no changes)

### Member

Already exists at `server/features/members/models/member.py`.

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| id | AutoField (PK) | No | Django auto-generated |
| name | CharField(255) | No | Full display name |
| first_name | CharField(255) | No | Default "" — may be empty |
| last_name | CharField(255) | No | Default "" — may be empty |
| birth_date | DateField | Yes | Source field for birthday filtering |
| gender | CharField(1) | Yes | M/F choices |
| status | FK(MemberStatus) | Yes | SET_NULL on delete |
| role | FK(Role) | Yes | SET_NULL on delete |
| ministries | M2M(Ministry) | — | |
| baptism_date | DateField | Yes | |
| is_active | BooleanField | No | Default True |
| created_at | DateTimeField | No | auto_now_add |

**Relevant fields for this feature**: `name`, `birth_date`, `is_active`

**Query pattern**: `Member.objects.filter(birth_date__month=month, is_active=True).exclude(birth_date__isnull=True)`

## New DTOs

### BirthdayDTO (Pydantic)

Transfer object from service to view layer.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Member's full name |
| birth_day | int | Day of month (1-31) |

No database migrations needed. No model changes.
