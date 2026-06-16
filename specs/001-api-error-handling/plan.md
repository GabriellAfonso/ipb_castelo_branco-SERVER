# Implementation Plan: API Error Handling

**Branch**: `001-api-error-handling` | **Date**: 2026-06-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-api-error-handling/spec.md`

## Summary

Unify API error handling into a single centralized exception handler that produces a canonical JSON format (`error_code`, `detail`, optional `field_errors`) for every error. Add `error_code` attributes to all domain exceptions, move scattered exception definitions and view-level validation into the proper layers, add structured logging, and handle unhandled exceptions with a JSON 500 response.

## Technical Context

**Language/Version**: Python 3.14.4

**Primary Dependencies**: Django 6.0.3, Django REST Framework 3.16.1, Pydantic 2.12.5, dependency-injector 4.48.3

**Storage**: PostgreSQL (via Django ORM)

**Testing**: pytest with Django test client

**Target Platform**: Linux server (behind nginx at `/ipbcb/`)

**Project Type**: Web service (REST API for Android client)

**Performance Goals**: N/A — error handling has negligible performance impact

**Constraints**: Single Android client; backward-incompatible response format change is acceptable (internal app)

**Scale/Scope**: ~6 feature modules, ~15 view classes, ~10 domain exception classes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Rule | Status | Notes |
|------|--------|-------|
| Views never access repositories — only services | PASS | No change to this pattern |
| Services never import HTTP objects | PASS | Validation moves FROM views TO services — services still won't use HTTP objects |
| Dependencies injected via container | PASS | No new injectable components needed for exception handler (it's a DRF setting, not DI) |
| DTOs between layers use Pydantic models | PASS | New validation DTOs may be needed where views currently do inline validation |
| All code in English | PASS | Exception codes and new code in English; existing Portuguese `detail` messages preserved |
| Features never import from each other | PASS | All domain exceptions stay in `core/domain/exceptions.py` |
| No hardcoded credentials | PASS | Not applicable |
| DEBUG = False in production | PASS | Handler may include exception message in DEBUG mode only |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-api-error-handling/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
server/
├── core/
│   ├── domain/
│   │   └── exceptions.py          # All domain exceptions with error_code attributes
│   ├── http/
│   │   └── exceptions.py          # Centralized exception handler (modify)
│   └── tests/
│       └── unit/
│           └── test_exception_handler.py  # Expand test coverage
├── features/
│   ├── accounts/
│   │   └── views/auth.py          # Remove manual try/except
│   ├── bible/
│   │   └── views/__init__.py      # Remove manual try/except
│   ├── schedule/
│   │   ├── views/schedule.py      # Remove manual try/except, move validation to service
│   │   └── services/              # Add input validation
│   └── songs/
│       ├── views/
│       │   ├── songs.py           # Remove manual try/except, move validation to service
│       │   └── register_plays.py  # Remove manual try/except, move validation to service
│       └── services/
│           └── register_plays_service.py  # Move SongsNotFoundError out
└── config/
    └── settings/base.py           # No change needed (handler already wired)
```

**Structure Decision**: Existing Django project structure. Changes are modifications to existing files — no new modules or packages needed beyond potentially new DTO classes in `core/application/dtos/`.
