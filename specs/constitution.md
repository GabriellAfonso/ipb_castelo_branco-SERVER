# Constitution

Rules that no domain can break. These apply globally across the entire system.

## Authentication & Authorization
- All protected endpoints require JWT (SimpleJWT) or Google OAuth 2.0
- Permission class `IsAuthenticated` on every authenticated view
- No endpoint bypasses auth unless explicitly marked public

## Data Integrity
- All user input validated via DRF serializer before reaching the database
- Uploaded files are validated by **decoded content**, never by filename or Content-Type,
  and the stored extension is derived from the detected format. `Model.save()` does not
  run field validators, so an `ImageField` alone validates nothing — go through
  `core.files.image_validation`.
- Uploads are size-checked before being read, and streamed to storage rather than loaded
  into memory
- No `.raw()` or string-formatted SQL with user input — ORM only
- No queries inside loops — use `select_related` / `prefetch_related`

## Architecture
- Features never import from each other directly — use `core/` or signals
- `core/` may contain models, but **only entities genuinely shared by two or more features**.
  If exactly one feature uses it, it belongs to that feature. Without this boundary `core`
  becomes a dumping ground. `core` became an installed Django app in feature 007, when the
  church service catalogue was needed by both `schedule` and `songs`.
- Views never access repositories — only services
- Services never import HTTP objects (`request`, `HttpResponse`)
- Repositories are the only layer that touches the ORM
- Dependencies injected via `dependency-injector` container (`config/di.py`)
- DTOs between layers use Pydantic models, not raw dicts

## Security
- No hardcoded credentials, secrets, or keys — environment variables only
- `DEBUG = False` in production — never expose tracebacks
- No password complexity validators — user chooses any password
- OpenAPI schema is intentionally public — accepted risk for internal church app
- `base.py` reads `DJANGO_SECRET_KEY` with **no fallback**. Each environment module
  supplies its own key. A default committed to the repository becomes the JWT signing
  key the moment production loads the wrong settings module, which turns a
  misconfiguration into a full authentication bypass rather than a degraded deploy.
- Any settings module that reassigns `SECRET_KEY` must also reassign
  `SIMPLE_JWT["SIGNING_KEY"]`. The dict is built once when `base.py` is imported and
  does not follow a later reassignment — the mismatch is silent.

## Code Standards
- All code in English (variables, functions, classes, files, comments, commits)
- PEP 8 with 100 character line limit
- Type hints on public function signatures
- Models always have `__str__`, `Meta.ordering`, `Meta.verbose_name`

## Deployment
- Base path `/ipbcb/` behind nginx — never hardcode absolute URLs
- Single client: Android app (`ipbcb-app`) — no web frontend

### Settings selection
Production running dev settings is silent — it boots normally, just without HSTS,
without secure cookies and with `DEBUG` on. Every rule below exists to make that
state impossible to reach quietly.

- `DJANGO_ENV` alone selects the settings module. **`DJANGO_SETTINGS_MODULE` never goes
  in `.env`**: `asgi.py` uses `os.environ.setdefault`, so a value in `.env` wins over
  the `DJANGO_ENV` selection without any error.
- Both compose files pin `DJANGO_ENV` and `DJANGO_SETTINGS_MODULE` under `environment:`,
  which takes precedence over `env_file:`. The `.env` cannot override the choice.
- `config.settings.dev` calls `reject_dev_settings_in_production()` and refuses to
  import when `DJANGO_ENV` is `prod`/`production`.
- CI runs `manage.py check --deploy --fail-level WARNING` against `config.settings.prod`
  with placeholder secrets. A check is silenced only via `SILENCED_SYSTEM_CHECKS` with
  the reason written beside it.
- CD asserts against the **running container** — not the config — that `SETTINGS_MODULE`
  is prod, `DEBUG` is off, HSTS is set, and `SIGNING_KEY == SECRET_KEY`.
- `SECURE_HSTS_PRELOAD` is deliberately off: browser preload is effectively
  irreversible. The HSTS header itself is set.
