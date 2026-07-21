# Feature Specification: Birthday Month Range Filter

**Feature Branch**: `005-birthday-month-range`

**Created**: 2026-07-21

**Status**: Complete

**Input**: User description: "Allow the birthdays endpoint to accept a month range in the format month=1-6 (start-end) in addition to a single month like month=7. When a range is provided, return birthdays from start_month through end_month inclusive, ordered by month then day ascending. Single month still works (backward compatible). Validation: both values must be integers 1-12, start <= end. Format: M or M-M."

## Clarifications

### Session 2026-07-21

- Q: Should response include `birth_month` field, and if so, for single-month queries too or only ranges? → A: Include `birth_month` in response for both single and range queries (consistent format).

## User Scenarios & Testing

### User Story 1 - View Birthdays Across a Month Range (Priority: P1)

A church member wants to see all birthdays in the first half of the year to plan celebrations ahead. They request `GET /ipbcb/members/birthdays/?month=1-6` and receive all members with birthdays from January through June, ordered by month then day ascending.

**Why this priority**: Primary new functionality. Enables users to view birthdays spanning multiple months in a single request, which is the core value of this feature.

**Independent Test**: Can be fully tested by sending a GET request with a range parameter (e.g., `month=1-6`) and verifying the response contains matching members from all months in the range, ordered by month then day.

**Acceptance Scenarios**:

1. **Given** members exist with birth dates in January, March, and June, **When** an authenticated member user requests `GET /ipbcb/members/birthdays/?month=1-6`, **Then** the response contains those members' names, genders, birth months, and birth days, ordered by month ascending then day ascending within each month.
2. **Given** members exist with birth dates in July and August, **When** an authenticated member user requests `GET /ipbcb/members/birthdays/?month=1-6`, **Then** those members are excluded from the results.
3. **Given** a range covering all twelve months (`month=1-12`), **When** an authenticated member user requests the endpoint, **Then** all members with birth dates are returned, ordered by month then day ascending.

---

### User Story 2 - Single Month Backward Compatibility (Priority: P1)

A church member uses the existing single-month format (`month=7`) and the endpoint continues to work exactly as before, returning birthdays for that month only, ordered by day ascending.

**Why this priority**: Backward compatibility is essential. Existing clients (Android app) must not break.

**Independent Test**: Can be fully tested by sending a GET request with a single month parameter and verifying the response matches the existing behavior.

**Acceptance Scenarios**:

1. **Given** members exist with birth dates in July, **When** an authenticated member user requests `GET /ipbcb/members/birthdays/?month=7`, **Then** the response contains those members ordered by day ascending (same as current behavior).
2. **Given** no members have birth dates in February, **When** an authenticated member user requests `GET /ipbcb/members/birthdays/?month=2`, **Then** the response is an empty list with a 200 status.

---

### User Story 3 - Range Validation Errors (Priority: P1)

A user sends a request with an invalid month range and receives a clear error message explaining the correct format.

**Why this priority**: Proper validation prevents confusing errors and guides users toward correct usage.

**Independent Test**: Can be tested by sending requests with various invalid range formats and verifying proper error responses.

**Acceptance Scenarios**:

1. **Given** a range where start is greater than end (e.g., `month=6-1`), **When** a user requests the endpoint, **Then** the system returns a 400 error indicating start month must be less than or equal to end month.
2. **Given** a range with out-of-bound values (e.g., `month=0-13`), **When** a user requests the endpoint, **Then** the system returns a 400 error indicating months must be between 1 and 12.
3. **Given** a range with non-numeric values (e.g., `month=a-b`), **When** a user requests the endpoint, **Then** the system returns a 400 error indicating the format must be M or M-M with valid integers.
4. **Given** a malformed range format (e.g., `month=1-2-3`), **When** a user requests the endpoint, **Then** the system returns a 400 error indicating invalid format.

---

### Edge Cases

- What happens when start and end month are the same (e.g., `month=7-7`)? It is treated equivalently to `month=7` and returns birthdays for that single month.
- What happens when the range covers months where no members have birthdays? An empty list with 200 status is returned.
- What happens when leading zeros are used (e.g., `month=01-06`)? They are accepted and parsed as integers 1 and 6.
- What happens when a member has no `birth_date` set (null)? They are excluded from results (existing behavior preserved).

## Requirements

### Functional Requirements

- **FR-001**: System MUST accept the `month` query parameter in two formats: single month (`M`, e.g., `7`) or range (`M-M`, e.g., `1-6`).
- **FR-002**: When a single month is provided, the system MUST behave identically to the existing endpoint (backward compatible).
- **FR-003**: When a range is provided, the system MUST return members with birthdays from start month through end month, inclusive.
- **FR-012**: Response MUST include `birth_month` field for all queries (single month and range), in addition to existing `birth_day`, name, and gender fields.
- **FR-004**: When a range is provided, results MUST be ordered by month ascending, then by day ascending within each month.
- **FR-005**: When a single month is provided, results MUST be ordered by day ascending (existing behavior).
- **FR-006**: Both month values in a range MUST be integers between 1 and 12.
- **FR-007**: In a range, start month MUST be less than or equal to end month.
- **FR-008**: System MUST return a 400 error with a descriptive message for invalid formats, out-of-range values, or start > end.
- **FR-009**: System MUST continue to require the `month` parameter (no change to existing requirement).
- **FR-010**: System MUST continue to exclude members with null `birth_date` from results.
- **FR-011**: System MUST continue to restrict access to users with `IsMemberUser` permission.

### Key Entities

- **Member**: Existing entity with `birth_date` field. The endpoint reads from this field to filter by month (or month range) and extract month and day.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can retrieve birthdays across multiple months in a single request using the range format.
- **SC-002**: Existing single-month requests produce identical results to the current endpoint behavior.
- **SC-003**: Range results are correctly ordered by month then day ascending.
- **SC-004**: Invalid range inputs return clear, actionable error messages with appropriate status codes.

## Assumptions

- The existing `birth_date` field on the Member model stores a full date; only month and day are relevant.
- Response always includes `birth_month` alongside name, gender, and `birth_day` — for both single-month and range queries (consistent format).
- The Android app will be updated to use the range format; single-month format remains supported indefinitely.
- No pagination is needed for range results; the member count is small enough for a church context.
