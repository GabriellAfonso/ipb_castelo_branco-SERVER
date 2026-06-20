# Research: Member Birthdays Endpoint

## R1: Filtering by birth month in Django ORM

**Decision**: Use `Member.objects.filter(birth_date__month=month)` with `.exclude(birth_date__isnull=True)`.

**Rationale**: Django's `__month` lookup extracts the month from a DateField and works on PostgreSQL natively (uses `EXTRACT`). Clean, ORM-native, no raw SQL needed.

**Alternatives considered**:
- Raw SQL with `EXTRACT(MONTH FROM birth_date)` — unnecessary, ORM handles it
- Python-side filtering — wasteful, loads all members into memory

## R2: Ordering by day of month

**Decision**: Use `.order_by(ExtractDay("birth_date"))` from `django.db.models.functions`.

**Rationale**: `ExtractDay` extracts the day component for ordering. Combined with `birth_date__month` filter, gives correct ordering within the requested month.

**Alternatives considered**:
- `order_by("birth_date")` — orders by full date including year, which is wrong for birthday lists
- Python-side sorting — unnecessary when DB can handle it

## R3: Response fields — which name field to use

**Decision**: Return `first_name` and `last_name` separately in the response. Include `name` as fallback display name.

**Rationale**: The Member model has three name fields: `name` (full), `first_name`, `last_name`. The spec says "member name". Returning `name` (the full name) is simplest and most aligned with the spec. The `first_name`/`last_name` fields were just added and may not be populated for all members yet.

**Alternatives considered**:
- Return only `first_name` + `last_name` — may be empty for existing members
- Return all three — over-engineering for this endpoint

**Final decision**: Return `name` (full name) and `birth_day` (integer day of month).

## R4: Month validation approach

**Decision**: Use a DRF serializer with `IntegerField(min_value=1, max_value=12)` to validate the `month` query parameter.

**Rationale**: Consistent with constitution rule (all user input validated via serializer). Provides clear error messages automatically. Handles type coercion (string "7" to int 7) and range validation.

**Alternatives considered**:
- Manual validation in view — violates constitution, more code
- Pydantic model — could work but DRF serializer integrates better with query params

## R5: Members domain lacks service/repository layers

**Decision**: Create `MemberRepository` (interface + Django implementation) and `MemberService` for the birthdays feature. Register in DI container.

**Rationale**: Constitution requires Views -> Services -> Repositories -> Models. The existing `MemberListAPIView` directly queries the ORM, but this feature must follow the architecture. The existing view is out of scope for refactoring in this feature.

**Alternatives considered**:
- Add query directly in view (like existing MemberListAPIView) — violates constitution
- Refactor existing view too — out of scope, separate task
