# Feature Specification: Member Birthdays Endpoint

**Feature Branch**: `004-member-birthdays`

**Created**: 2026-06-20

**Status**: Complete

**Input**: User description: "Birthdays endpoint for the members domain. GET /ipbcb/members/birthdays/?month={1-12} returns members whose birth_date falls in the given month. Response includes member name and birth day (day of month only). Results ordered by day ascending. Permission: IsMemberUser. Source field is the existing birth_date on the Member model. month query parameter is required."

## User Scenarios & Testing

### User Story 1 - View Birthdays by Month (Priority: P1)

A church member wants to see who has birthdays in a given month so they can plan celebrations or send greetings. They request the list for a specific month and receive the names and birth days of all members born in that month, sorted by day.

**Why this priority**: Core and only functionality of this feature. Delivers immediate value by enabling birthday awareness within the church community.

**Independent Test**: Can be fully tested by sending a GET request with a valid month parameter and verifying the response contains matching members ordered by day.

**Acceptance Scenarios**:

1. **Given** members exist with birth dates in July, **When** an authenticated member user requests `GET /ipbcb/members/birthdays/?month=7`, **Then** the response contains those members' names, genders, and birth days (day of month only), ordered by day ascending.
2. **Given** no members have birth dates in February, **When** an authenticated member user requests `GET /ipbcb/members/birthdays/?month=2`, **Then** the response is an empty list with a 200 status.
3. **Given** multiple members share the same birth day in a month, **When** the list is requested, **Then** all members for that day appear in the results.

---

### User Story 2 - Invalid Month Handling (Priority: P1)

A user sends a request with an invalid or missing month parameter and receives a clear error message.

**Why this priority**: Essential for a robust endpoint. Without proper validation, bad requests could cause confusing errors.

**Independent Test**: Can be tested by sending requests with invalid month values and verifying proper error responses.

**Acceptance Scenarios**:

1. **Given** no month parameter is provided, **When** a user requests `GET /ipbcb/members/birthdays/`, **Then** the system returns a 400 error indicating the month parameter is required.
2. **Given** an out-of-range month value (e.g., 0, 13, -1), **When** a user requests the endpoint, **Then** the system returns a 400 error indicating the month must be between 1 and 12.
3. **Given** a non-numeric month value (e.g., "abc"), **When** a user requests the endpoint, **Then** the system returns a 400 error indicating the month must be a valid integer.

---

### Edge Cases

- What happens when a member has no `birth_date` set (null)? They are excluded from results.
- What happens when the month parameter is a valid integer but with leading zeros (e.g., "07")? It is accepted and treated as month 7.
- What happens when an unauthenticated user accesses the endpoint? They receive a 401 Unauthorized response.
- What happens when an authenticated user without `IsMemberUser` permission accesses the endpoint? They receive a 403 Forbidden response.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a `GET /ipbcb/members/birthdays/` endpoint that returns members with birthdays in the specified month.
- **FR-002**: System MUST require a `month` query parameter with an integer value between 1 and 12.
- **FR-003**: System MUST return each matching member's name, gender, and birth day (day of month only, not the full date).
- **FR-004**: System MUST order results by birth day ascending.
- **FR-005**: System MUST restrict access to users with `IsMemberUser` permission.
- **FR-006**: System MUST return a 400 error when the `month` parameter is missing, non-numeric, or outside the 1-12 range.
- **FR-007**: System MUST exclude members whose `birth_date` is null from results.

### Key Entities

- **Member**: Existing entity with `birth_date` field. The endpoint reads from this field to filter by month and extract day of month.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Authenticated member users can retrieve a birthday list for any valid month in a single request.
- **SC-002**: Results are correctly filtered by the requested month and sorted by day ascending.
- **SC-003**: Invalid requests (missing/bad month parameter) return clear, actionable error messages.
- **SC-004**: Unauthorized or insufficiently privileged users are denied access with appropriate status codes.

## Assumptions

- The existing `birth_date` field on the Member model stores a full date (year, month, day); only month and day are relevant for this feature.
- The response includes the member's name (using existing name fields on the Member model), gender (`"M"`, `"F"`, or `null`), and the day of month as an integer.
- No year-based filtering is needed; birthdays repeat annually.
- The endpoint is read-only (GET); no write operations are involved.
