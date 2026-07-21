# Tasks: Birthday Month Range Filter

**Input**: Design documents from `specs/005-birthday-month-range/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks grouped by user story. All three user stories are P1 but have natural dependencies: US1 (range query) requires foundational changes, US2 (backward compat) validates no regression, US3 (validation errors) extends the serializer.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Foundational (Shared Changes)

**Purpose**: DTO and repository changes that all user stories depend on

- [x] T001 [P] Add `birth_month: int` field to `BirthdayDTO` in `server/features/members/dtos.py`
- [x] T002 [P] Replace `BirthdayQueryParamSerializer.month` IntegerField with custom `MonthRangeField` that accepts `M` and `M-M` formats, validates 1-12 range and start <= end, returns `(start_month, end_month)` tuple in `server/features/members/serializers/birthday_serializer.py`
- [x] T003 Add `birth_month` to `BirthdayResponseSerializer` as `IntegerField` in `server/features/members/serializers/birthday_serializer.py` (depends on T001)
- [x] T004 Replace `list_birthdays_by_month(month: int)` with `list_birthdays_by_month_range(start_month: int, end_month: int)` in repository Protocol in `server/features/members/repositories/interfaces.py` (depends on T001)
- [x] T005 Implement `list_birthdays_by_month_range` in `DjangoMemberRepository`: filter `birth_date__month__gte`/`__lte`, annotate with `ExtractMonth` and `ExtractDay`, order by month then day, return `BirthdayDTO` with `birth_month` in `server/features/members/repositories/member_repository.py` (depends on T001, T004)
- [x] T006 Replace `list_birthdays_by_month` with `list_birthdays_by_month_range(start_month: int, end_month: int)` in `MemberService` in `server/features/members/services/member_service.py` (depends on T004, T005)
- [x] T007 Update `MemberBirthdaysAPIView.get` to extract `(start_month, end_month)` tuple from validated serializer data and pass to `member_service.list_birthdays_by_month_range` in `server/features/members/views/birthdays.py` (depends on T002, T006)

**Checkpoint**: All layers updated. Endpoint accepts both formats, returns `birth_month` in response.

---

## Phase 2: User Story 1 — View Birthdays Across a Month Range (Priority: P1)

**Goal**: Users can request `?month=1-6` and get birthdays from January through June, ordered by month then day.

**Independent Test**: `GET /api/members/birthdays/?month=1-6` returns members from all months in range, ordered correctly.

### Tests for User Story 1

- [x] T008 [P] [US1] Add integration test: range query `month=1-6` returns members from multiple months ordered by month then day in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T009 [P] [US1] Add integration test: range `month=1-12` returns all members with birth dates in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T010 [P] [US1] Add integration test: range excludes members outside range (e.g., July member excluded from `month=1-6`) in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T011 [P] [US1] Add integration test: range `month=7-7` returns same results as single month in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T012 [P] [US1] Add unit test for `list_birthdays_by_month_range` in `FakeMemberRepository` in `server/features/members/tests/unit/test_member_service.py`

**Checkpoint**: Range query works end-to-end with correct ordering and filtering.

---

## Phase 3: User Story 2 — Single Month Backward Compatibility (Priority: P1)

**Goal**: Existing `?month=7` format produces identical behavior, now with `birth_month` field added.

**Independent Test**: `GET /api/members/birthdays/?month=7` returns same members/ordering as before, plus `birth_month` field.

### Tests for User Story 2

- [x] T013 [P] [US2] Update existing integration tests to assert `birth_month` field present in response in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T014 [P] [US2] Add integration test: single month `month=7` returns `birth_month: 7` for all entries in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T015 [P] [US2] Add integration test: leading zeros `month=07` still accepted in `server/features/members/tests/integration/test_birthdays_api.py`

**Checkpoint**: All existing tests pass with updated assertions. No regression.

---

## Phase 4: User Story 3 — Range Validation Errors (Priority: P1)

**Goal**: Invalid range inputs return clear 400 errors with descriptive messages.

**Independent Test**: Various invalid inputs (`month=6-1`, `month=0-13`, `month=a-b`, `month=1-2-3`) all return 400 with specific messages.

### Tests for User Story 3

- [x] T016 [P] [US3] Add integration test: `month=6-1` (start > end) returns 400 with descriptive message in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T017 [P] [US3] Add integration test: `month=0-13` (out of range) returns 400 in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T018 [P] [US3] Add integration test: `month=a-b` (non-numeric) returns 400 in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T019 [P] [US3] Add integration test: `month=1-2-3` (malformed) returns 400 in `server/features/members/tests/integration/test_birthdays_api.py`
- [x] T020 [P] [US3] Add integration test: missing `month` param still returns 400 (existing behavior) in `server/features/members/tests/integration/test_birthdays_api.py`

**Checkpoint**: All validation paths covered with clear error messages matching contract.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T021 Update spec.md status from "Draft" to "Complete" in `specs/005-birthday-month-range/spec.md`
- [x] T022 Run full test suite and validate all tests pass
- [x] T023 Run quickstart.md validation scenarios manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: No external dependencies — modifies existing files
- **Phase 2 (US1)**: Depends on Phase 1 completion
- **Phase 3 (US2)**: Depends on Phase 1 completion (can run parallel with Phase 2)
- **Phase 4 (US3)**: Depends on T002 (serializer validation) from Phase 1
- **Phase 5 (Polish)**: Depends on all previous phases

### Within Phase 1

```
T001 (DTO) ──┬──→ T003 (response serializer)
             ├──→ T004 (interface) ──→ T005 (repository) ──→ T006 (service) ──→ T007 (view)
T002 (query serializer) ──────────────────────────────────────────────────────→ T007 (view)
```

### Parallel Opportunities

- T001 and T002 can run in parallel (different concerns)
- All test tasks within a phase can run in parallel
- Phase 2 (US1) and Phase 3 (US2) can run in parallel after Phase 1

---

## Parallel Example: Phase 1

```bash
# Parallel pair 1 (no dependencies):
Task T001: "Add birth_month to BirthdayDTO in server/features/members/dtos.py"
Task T002: "Create MonthRangeField in server/features/members/serializers/birthday_serializer.py"
```

## Parallel Example: User Story Tests

```bash
# All US1 tests can run in parallel:
Task T008: "Integration test: range query month=1-6"
Task T009: "Integration test: range month=1-12"
Task T010: "Integration test: range excludes out-of-range"
Task T011: "Integration test: range month=7-7 equals single"
Task T012: "Unit test: list_birthdays_by_month_range"
```

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2)

1. Complete Phase 1: All foundational changes (T001-T007)
2. Complete Phase 2: Range query tests (T008-T012)
3. **STOP and VALIDATE**: Range queries work, single month still works
4. Continue to Phase 3-4 for full coverage

### Sequential Delivery

1. Phase 1 (Foundational) → All layers updated
2. Phase 2 (US1: Range) → Core feature works
3. Phase 3 (US2: Backward compat) → Regression tests confirm
4. Phase 4 (US3: Validation) → Error paths covered
5. Phase 5 (Polish) → Spec updated, full suite green

---

## Notes

- No new files created — all changes to existing files
- No migrations needed — no model changes
- `birth_month` addition to response is backward-compatible (additive field)
- `MonthRangeField` is the key new component — custom DRF serializer field
- Commit after each phase for clean history
