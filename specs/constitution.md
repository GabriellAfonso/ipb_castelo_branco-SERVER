# Constitution

Rules that no domain can break. These apply globally across the entire system.

## Authentication & Authorization
- All protected endpoints require JWT (SimpleJWT) or Google OAuth 2.0
- Permission class `IsAuthenticated` on every authenticated view
- No endpoint bypasses auth unless explicitly marked public
- Every path that checks a password is behind failed-attempt lockout (`django-axes`), the API
  login and the Django admin login alike. DRF throttles do not reach the admin — it is a plain
  Django view — and the password policy below allows six-character passwords, so the lockout is
  the only thing standing between a public `/ipbcb/admin/` and an offline-speed guessing loop.
  The lockout key is the `(username, address)` pair; neither half alone is acceptable, and the
  reasoning is in `specs/008-login-brute-force-lockout/plan.md` D-3.

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
- Never `**request.data` or `int(...)` a raw request field directly. A body that is not a
  JSON object, or a field that will not coerce, raises outside the exception handler's
  reach and surfaces as a 500 — which tells the client to retry a request that can never
  succeed, and buries real incidents in client-caused noise. Go through
  `core.http.parsing.require_object_body` / `require_int`, which raise the domain
  `ValidationError` the handler already maps to 400.

## Architecture
- Features never import from each other directly — use `core/` or signals
- `core/` may contain models, but **only entities genuinely shared by two or more features**.
  If exactly one feature uses it, it belongs to that feature. Without this boundary `core`
  becomes a dumping ground. `core` became an installed Django app in feature 007, when the
  church service catalogue was needed by both `schedule` and `songs`.
- Views never access repositories — only services
- Services never import HTTP objects (`request`, `HttpResponse`).
  **One standing exception: `LoginService.login()` receives the `request`.**
  `django-axes` records the client address and user agent of each failed attempt, and its
  authentication backend raises `AxesBackendRequestParameterRequired` when
  `django.contrib.auth.authenticate()` is called without one — so the choice is not "pure service
  or impure service", it is "lockout or no lockout". Wrapping the library behind a Protocol taking
  a Pydantic client context does not avoid it either: the library's own handler wants an
  `HttpRequest` too, so the wrapper would have to fake one. Full reasoning in
  `specs/008-login-brute-force-lockout/plan.md` D-1. No other service takes an HTTP parameter.
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

### Client IP
- Resolve it through `ipware` with `proxy_order="right-most"` — never by reading
  `X-Forwarded-For` directly. nginx sets the header with `$proxy_add_x_forwarded_for`,
  which appends the observed address to whatever the caller sent, so the left-most entry
  is attacker-controlled. Three consumers must agree: DRF throttling (`NUM_PROXIES`), the
  axes lockout (`AXES_IPWARE_PROXY_ORDER`) and the request log. A log that disagrees with
  the other two is worst exactly when it matters — investigating what they blocked.

### Caching
- Any response whose body depends on who asked declares `Cache-Control: private, no-store`
  and `Vary: Authorization`, via the `private=True` flag on
  `core.http.utils._not_modified_or_response`. A shared cache keys on the URL, not on the
  Authorization header, so an undeclared `/api/me/profile/` response would be handed to the
  next caller of that URL. Public data stays undeclared, so a cache in front is free to
  store it.

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

### Dependencies
- CI runs `pip-audit -r requirements.txt --strict` as a **blocking** gate. It is the only
  check that looks at the dependencies rather than at our own code, and the dependencies
  are most of what runs in production — Pillow decodes uploaded bytes, Django serves every
  request. Blocking on purpose: a published advisory does not announce itself, and a red
  build is the only reminder that does not rely on remembering to look. A badly timed
  advisory is unblocked with `--ignore-vuln <id>` plus a dated comment saying why, never by
  dropping the gate.
- Declare the canonical package, never an alias that only depends on it. `requirements.txt`
  once pinned `dotenv`, a package whose own summary reads "Deprecated package" and whose
  sole content is a dependency on `python-dotenv`. It sits on an obvious typosquat name,
  is maintained by someone else, and runs at `config/settings/base.py` import time —
  before anything else in the application. The failure mode is silent: `pip install dotenv`
  to "fix" an ImportError puts it right back.

### Secrets and service boundaries
- Each service gets only the secrets it needs. `./.env` is the application's file
  (Django + Postgres); Grafana reads `./.env.grafana`. Never point a public-facing
  sidecar at the application's env file — it puts `DJANGO_SECRET_KEY` one `printenv`
  away from anyone who reaches that container.
- Every per-service env file is git-ignored. `.gitignore` must use `.env.*`, not a bare
  `.env`, which matches only the exact name.
- **Accepted risk:** the Postgres container also reads `./.env`, so it holds
  `DJANGO_SECRET_KEY` and `GOOGLE_CLIENT_ID` it never uses. Splitting it out would
  duplicate `POSTGRES_USER`/`POSTGRES_PASSWORD` across two files that can drift. Unlike
  Grafana, this container publishes no port and exposes no HTTP surface, so it is blast
  radius rather than an entry vector. Do not re-raise this.

### Metrics endpoint
- `/ipbcb/metrics` is blocked at nginx (`location = /ipbcb/metrics { return 404; }`).
  It is unauthenticated by nature and leaks the endpoint map, request volumes, latencies
  and the login success/failure counters. The block lives in the `nginx-deploy`
  repository, so this is its only record inside this project.
- Prometheus is unaffected: it scrapes `ipbcb-server-prod:8000/metrics` over the Docker
  network, never through nginx. Dashboards are at `/ipbcb/gfd/`, behind Grafana's login.
- `SECURE_REDIRECT_EXEMPT` therefore holds `^metrics$` only. Under ASGI,
  `FORCE_SCRIPT_NAME` leaves `request.path` as the path nginx sent, so `^metrics$` matches
  the internal scrape and `^ipbcb/metrics$` matched the public one — keeping the second
  pattern served metrics over plain HTTP to the internet.
