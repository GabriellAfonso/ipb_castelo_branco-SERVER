# Research: Birthday Month Range Filter

## Decision 1: Month Parameter Parsing Strategy

**Decision**: Use a custom DRF serializer field that accepts both `M` and `M-M` formats, returning a tuple `(start_month, end_month)`. For single month input, return `(M, M)` so downstream code always works with a range.

**Rationale**: Normalizing to a tuple at the serializer boundary keeps service and repository layers simple — they always receive a range. No conditional branching needed downstream.

**Alternatives considered**:
- Separate query params (`month_start`, `month_end`): Breaks backward compatibility, more verbose.
- Parse in the view manually: Puts validation logic outside the serializer, violates project conventions.

## Decision 2: Repository Query Approach

**Decision**: Use Django ORM `birth_date__month__gte` and `birth_date__month__lte` with `ExtractMonth` for ordering. Add a new method `list_birthdays_by_month_range(start_month, end_month)` to replace single-month method.

**Rationale**: Single method handles both cases since `(7, 7)` is equivalent to single month. ORM month range filters are well-supported in Django/PostgreSQL.

**Alternatives considered**:
- Keep two separate methods (single + range): Redundant — range subsumes single.
- Use `__month__in=range(start, end+1)`: Works but less efficient than `gte`/`lte` for PostgreSQL.

## Decision 3: Ordering for Range Results

**Decision**: Order by `ExtractMonth("birth_date")` then `ExtractDay("birth_date")`. For single month queries, month ordering is a no-op (all same month), so results are still ordered by day — backward compatible.

**Rationale**: Unified ordering logic works for both single and range without branching.

## Decision 4: BirthdayDTO — Adding birth_month

**Decision**: Add `birth_month: int` field to `BirthdayDTO`. Response serializer includes `birth_month` for all queries (single and range). This is a backward-compatible addition (new field, no removals).

**Rationale**: Clarification session confirmed consistent format. Adding a field doesn't break existing Android clients — they ignore unknown fields.

## Decision 5: Service Layer Changes

**Decision**: Replace `list_birthdays_by_month(month: int)` with `list_birthdays_by_month_range(start_month: int, end_month: int)`. Service is a thin passthrough to repository.

**Rationale**: Cleaner API. Old method name would be misleading for range queries.
