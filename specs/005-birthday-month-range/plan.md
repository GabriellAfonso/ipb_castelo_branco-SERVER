# Implementation Plan: Birthday Month Range Filter

**Branch**: `005-birthday-month-range` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-birthday-month-range/spec.md`

## Summary

Extend the existing `GET /api/members/birthdays/` endpoint to accept a month range (`month=1-6`) in addition to a single month (`month=7`). Requires changes to the query param serializer (validation), service (parsing logic), repository (range query), DTO (add `birth_month`), and response serializer. No model or migration changes needed.

## Technical Context

**Language/Version**: Python 3.14 (pyenv)

**Primary Dependencies**: Django 5.x, Django REST Framework, dependency-injector, Pydantic

**Storage**: PostgreSQL (existing Member model, no schema changes)

**Testing**: pytest + DRF APIClient

**Target Platform**: Linux server behind nginx (`/ipbcb/` prefix)

**Project Type**: Web service (REST API)

**Performance Goals**: N/A (church-scale, ~hundreds of members)

**Constraints**: Backward compatible — single month format must keep working identically

**Scale/Scope**: Single endpoint change, ~7 files touched

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Rule | Status | Notes |
|------|--------|-------|
| Views only call services | PASS | View delegates to service |
| Services don't import HTTP objects | PASS | Service receives parsed ints |
| Repositories own ORM queries | PASS | Range query in repository only |
| DTOs via Pydantic | PASS | BirthdayDTO updated with birth_month |
| DI via dependency-injector | PASS | No new services/repos needed |
| All code in English | PASS | |
| Input validated via serializer | PASS | Custom serializer field handles M and M-M |
| No `.raw()` SQL | PASS | ORM `__month__gte`/`__month__lte` |
| Domain errors for domain validation | PASS | Month parsing validation stays at serializer level (input boundary) |

All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-birthday-month-range/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── birthdays-endpoint.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
server/features/members/
├── serializers/
│   └── birthday_serializer.py    # Update: replace IntegerField with custom MonthRangeField
├── services/
│   └── member_service.py         # Update: new method or extend existing for range
├── repositories/
│   ├── interfaces.py             # Update: add range method signature
│   └── member_repository.py      # Update: add range query method
├── dtos.py                       # Update: add birth_month to BirthdayDTO
├── views/
│   └── birthdays.py              # Update: pass parsed range to service
└── tests/
    ├── integration/
    │   └── test_birthdays_api.py  # Update: add range tests
    └── unit/
        └── test_member_service.py # Update: add range tests
```

**Structure Decision**: No new files needed. All changes fit existing module structure.
