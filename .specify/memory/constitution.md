# IPBCB Backend Constitution

Rules that no domain can break. These apply globally across the entire system.

## Authentication & Authorization
- All protected endpoints require JWT (SimpleJWT) or Google OAuth 2.0
- Permission class `IsAuthenticated` on every authenticated view
- No endpoint bypasses auth unless explicitly marked public

## Data Integrity
- All user input validated via DRF serializer or Pydantic DTO before reaching the database
- No `.raw()` or string-formatted SQL with user input — ORM only
- No queries inside loops — use `select_related` / `prefetch_related`

## Architecture
- Features never import from each other directly — use `core/` or signals
- Views never access repositories — only services
- Services never import HTTP objects (`request`, `HttpResponse`)
- Repositories are the only layer that touches the ORM
- Dependencies injected via `dependency-injector` container (`config/container.py`)
- DTOs between layers use Pydantic models, not raw dicts

## Security
- No hardcoded credentials, secrets, or keys — environment variables only
- `DEBUG = False` in production — never expose tracebacks
- No password complexity validators — user chooses any password
- OpenAPI schema is intentionally public — accepted risk for internal church app

## Code Standards
- All code in English (variables, functions, classes, files, comments, commits)
- PEP 8 with 100 character line limit
- Type hints on public function signatures
- Models always have `__str__`, `Meta.ordering`, `Meta.verbose_name`

## Deployment
- Base path `/ipbcb/` behind nginx — never hardcode absolute URLs
- Single client: Android app (`ipbcb-app`) — no web frontend

## Governance
- Constitution supersedes all other specs
- Changes require updating both spec and code together

**Version**: 1.0 | **Ratified**: 2026-06-16
