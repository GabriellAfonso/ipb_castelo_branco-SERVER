# Implementation Plan: Member Birthdays Endpoint

**Branch**: `004-member-birthdays` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-member-birthdays/spec.md`

## Summary

Add a `GET /api/members/birthdays/?month={1-12}` endpoint that returns members whose `birth_date` falls in the given month, ordered by day ascending. Follows clean architecture (view -> service -> repository) using the existing songs/gallery patterns. Requires creating the members service and repository layers that currently don't exist.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Django 5.x, Django REST Framework, dependency-injector, Pydantic

**Storage**: PostgreSQL (existing `members_member` table, `birth_date` column)

**Testing**: pytest + pytest-django

**Target Platform**: Linux server (behind nginx at `/ipbcb/`)

**Project Type**: Web service (REST API for Android app)

**Performance Goals**: Standard — small dataset (church members, likely <500 rows)

**Constraints**: Must follow clean architecture per constitution

**Scale/Scope**: Single endpoint addition to existing members domain

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Rule | Status | Notes |
|------|--------|-------|
| Views never access repositories — only services | PASS | View will call `MemberService.list_birthdays_by_month()` |
| Services never import HTTP objects | PASS | Service receives `month: int`, returns list of DTOs |
| Repositories are only layer touching ORM | PASS | Repository handles `Member.objects.filter(birth_date__month=...)` |
| Dependencies injected via container | PASS | Will register `member_repository` and `member_service` in `config/di.py` |
| DTOs between layers use Pydantic | PASS | Will use Pydantic model for birthday data |
| All user input validated via serializer/Pydantic | PASS | Month validated via query parameter serializer |
| Permission class on authenticated view | PASS | `[IsAuthenticated, IsMemberUser]` |
| No hardcoded credentials | PASS | N/A — read-only query |
| All code in English | PASS | All names and comments in English |

No violations. Gate passes.

## Project Structure

### Documentation (this feature)

```text
specs/004-member-birthdays/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── birthdays-endpoint.md
└── tasks.md              # Created by /speckit-tasks
```

### Source Code (new/modified files)

```text
server/features/members/
├── models/
│   └── member.py                    # Existing (no changes)
├── repositories/
│   ├── __init__.py                  # New
│   ├── interfaces.py                # New — abstract MemberRepository
│   └── member_repository.py         # New — DjangoMemberRepository
├── services/
│   ├── __init__.py                  # New
│   └── member_service.py            # New — MemberService
├── serializers/
│   ├── __init__.py                  # New
│   └── birthday_serializer.py       # New — BirthdaySerializer
├── dtos.py                          # New — BirthdayDTO
├── views/
│   ├── members.py                   # Existing (no changes for this feature)
│   └── birthdays.py                 # New — MemberBirthdaysAPIView
├── urls.py                          # Modified — add birthdays route
└── tests/
    ├── integration/
    │   └── test_birthdays_api.py     # New
    └── unit/
        └── test_member_service.py    # New

server/config/
└── di.py                            # Modified — add members DI entries
```

**Structure Decision**: Follows existing domain pattern (songs/gallery). Creates the missing service/repository layers for members domain.
