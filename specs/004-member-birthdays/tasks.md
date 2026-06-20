# Tasks: Member Birthdays Endpoint

**Input**: Design documents from `specs/004-member-birthdays/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — spec requires regression and integration tests per project guidelines.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the members domain service/repository layers that don't exist yet

- [x] T001 [P] Create repository interface in `server/features/members/repositories/interfaces.py` with abstract `list_birthdays_by_month(month: int)` method
- [x] T002 [P] Create BirthdayDTO Pydantic model in `server/features/members/dtos.py` with `name: str` and `birth_day: int` fields
- [x] T003 [P] Create `server/features/members/repositories/__init__.py`
- [x] T004 [P] Create `server/features/members/services/__init__.py`
- [x] T005 [P] Create `server/features/members/serializers/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Repository and service implementations that both user stories depend on

- [x] T006 Implement `DjangoMemberRepository` in `server/features/members/repositories/member_repository.py` with `list_birthdays_by_month(month: int)` — filter `Member.objects.filter(birth_date__month=month, is_active=True)`, exclude null `birth_date`, order by `ExtractDay("birth_date")`, return list of `BirthdayDTO`
- [x] T007 Implement `MemberService` in `server/features/members/services/member_service.py` with `list_birthdays_by_month(month: int)` — delegates to repository
- [x] T008 Register `member_repository` and `member_service` in `server/config/di.py` and add `features.members.views.birthdays` to wiring config

**Checkpoint**: Service/repository layers ready. User story implementation can begin.

---

## Phase 3: User Story 1 - View Birthdays by Month (Priority: P1) — MVP

**Goal**: Authenticated member users can retrieve birthday list for any valid month

**Independent Test**: `GET /api/members/birthdays/?month=7` returns matching members ordered by day ascending; empty month returns empty list

### Tests for User Story 1

- [x] T009 [P] [US1] Write integration test `test_member_returns_birthdays_for_month` in `server/features/members/tests/integration/test_birthdays_api.py` — create members with known birth dates, request month, verify response contains correct names and days ordered ascending
- [x] T010 [P] [US1] Write integration test `test_empty_month_returns_empty_list` in `server/features/members/tests/integration/test_birthdays_api.py` — request month with no matching members, verify 200 with empty list
- [x] T011 [P] [US1] Write integration test `test_excludes_null_birth_date` in `server/features/members/tests/integration/test_birthdays_api.py` — create member with null birth_date, verify excluded from results
- [x] T012 [P] [US1] Write integration test `test_excludes_inactive_members` in `server/features/members/tests/integration/test_birthdays_api.py` — create inactive member with matching birth_date, verify excluded
- [x] T013 [P] [US1] Write unit test `test_list_birthdays_by_month` in `server/features/members/tests/unit/test_member_service.py` — mock repository, verify service delegates correctly

### Implementation for User Story 1

- [x] T014 [P] [US1] Create `BirthdayResponseSerializer` in `server/features/members/serializers/birthday_serializer.py` with `name` (CharField) and `birth_day` (IntegerField) fields
- [x] T015 [US1] Create `MemberBirthdaysAPIView` in `server/features/members/views/birthdays.py` — `permission_classes = [IsAuthenticated, IsMemberUser]`, inject `MemberService`, call `list_birthdays_by_month(month)`, serialize with `BirthdayResponseSerializer`, return `{"birthdays": [...]}`
- [x] T016 [US1] Add birthdays URL route in `server/features/members/urls.py` — `path("api/members/birthdays/", MemberBirthdaysAPIView.as_view(), name="members_birthdays")`

**Checkpoint**: Birthday listing works for valid months. Run tests T009-T013 to verify.

---

## Phase 4: User Story 2 - Invalid Month Handling (Priority: P1)

**Goal**: Invalid or missing month parameter returns clear 400 error

**Independent Test**: Requests with missing, non-numeric, or out-of-range month values return 400 with descriptive error messages

### Tests for User Story 2

- [x] T017 [P] [US2] Write integration test `test_missing_month_returns_400` in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T018 [P] [US2] Write integration test `test_invalid_month_returns_400` in `server/features/members/tests/integration/test_birthdays_api.py` — test values: 0, 13, -1, "abc"
- [x] T019 [P] [US2] Write integration test `test_unauthenticated_returns_401` in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T020 [P] [US2] Write integration test `test_non_member_returns_403` in `server/features/members/tests/integration/test_birthdays_api.py`

### Implementation for User Story 2

- [x] T021 [US2] Create `BirthdayQueryParamSerializer` in `server/features/members/serializers/birthday_serializer.py` — `month = IntegerField(required=True, min_value=1, max_value=12)`, use in view to validate query params before calling service

**Checkpoint**: All validation and auth error paths return correct status codes. Run tests T017-T020 to verify.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T022 Run full test suite for members domain: `pytest server/features/members/tests/ -v`
- [x] T023 Run quickstart.md validation scenarios
- [x] T024 Update `specs/004-member-birthdays/spec.md` status from Draft to Complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — all tasks parallelizable
- **Foundational (Phase 2)**: Depends on Phase 1 (T001, T002 specifically)
- **US1 (Phase 3)**: Depends on Phase 2 (T006, T007, T008)
- **US2 (Phase 4)**: Depends on Phase 2 (T008 for view wiring). Can run in parallel with US1.
- **Polish (Phase 5)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational — no dependency on US2
- **User Story 2 (P1)**: After Foundational — no dependency on US1. Shares view file with US1 so coordinate T015 and T021.

### Within Each User Story

- Tests written first (should fail before implementation)
- Serializer before view
- View before URL route
- All tests pass at checkpoint

### Parallel Opportunities

- T001-T005: All parallelizable (different files)
- T009-T013: All parallelizable (same file but independent test methods)
- T014 parallel with T009-T013 (different files)
- T017-T020: All parallelizable
- US1 and US2 can proceed in parallel after Phase 2

---

## Parallel Example: Phase 1

```text
# All setup tasks in parallel (different files):
T001: Create repository interface in repositories/interfaces.py
T002: Create BirthdayDTO in dtos.py
T003: Create repositories/__init__.py
T004: Create services/__init__.py
T005: Create serializers/__init__.py
```

## Parallel Example: User Story 1 Tests

```text
# All US1 tests in parallel:
T009: test_member_returns_birthdays_for_month
T010: test_empty_month_returns_empty_list
T011: test_excludes_null_birth_date
T012: test_excludes_inactive_members
T013: test_list_birthdays_by_month (unit)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (5 tasks)
2. Complete Phase 2: Foundational (3 tasks)
3. Complete Phase 3: User Story 1 (8 tasks)
4. **STOP and VALIDATE**: Test birthday listing works end-to-end
5. Deploy if ready — users can already look up birthdays

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add User Story 1 → Birthday listing works → Deploy (MVP!)
3. Add User Story 2 → Validation hardened → Deploy
4. Polish → Full quality pass → Final deploy

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- T015 and T021 both touch `views/birthdays.py` — if doing US1 and US2 in parallel, coordinate on this file
- Commit after each phase completion
- Total: 24 tasks across 5 phases
