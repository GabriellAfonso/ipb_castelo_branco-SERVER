# Research: Application Metrics with Prometheus & Grafana

## R1: django-prometheus vs raw prometheus_client

**Decision**: Use `django-prometheus` package

**Rationale**: `django-prometheus` wraps `prometheus_client` and provides:
- Auto-instrumented middleware for RED metrics (request count, latency histogram, error rate by endpoint/method/status)
- Drop-in database engine wrapper for query count/duration metrics
- Automatic `/metrics` endpoint via `django_prometheus.urls`
- Zero custom code for infrastructure metrics — just config changes

**Alternatives considered**:
- Raw `prometheus_client` with custom middleware: more control but requires reimplementing what django-prometheus already provides. Unnecessary for this scope.
- `django-prometheus` + custom counters via `prometheus_client`: best of both — auto RED/DB metrics + targeted business counters. **This is the chosen approach.**

## R2: /metrics endpoint routing — outside /ipbcb/ prefix

**Decision**: Add `django_prometheus.urls` directly in `config/urls.py` at root level

**Rationale**: Django URL patterns in `config/urls.py` already live at root level (`health/`, `admin/`, `api/schema/`). The `/ipbcb/` prefix is applied only in production by nginx reverse proxy + `FORCE_SCRIPT_NAME`. Since Prometheus scrapes within the Docker network (bypassing nginx), the `/metrics` path resolves correctly at root.

No special handling needed — `path("", include("django_prometheus.urls"))` adds `/metrics` at the same level as `/health/`.

**Alternatives considered**:
- Separate Django app with its own urlconf: unnecessary complexity for a single endpoint.
- Custom view wrapping `prometheus_client.generate_latest()`: would lose django-prometheus auto-discovery. Not needed.

## R3: Business metrics architecture — service layer instrumentation

**Decision**: Define all custom metrics in `core/metrics.py` as module-level `prometheus_client` objects. Import and call `.inc()` / `.observe()` directly in service methods.

**Rationale**:
- `prometheus_client` metrics are module-level singletons by design (registered in a global registry). This aligns with how the library is meant to be used.
- No need for dependency injection — metrics are stateless counters, not services with behavior. Adding them to the DI container would be over-engineering.
- Services already import from `core.*` (e.g., `core.domain.exceptions`), so `core.metrics` follows the same pattern.
- Clean architecture preserved: services import a core infrastructure module, not HTTP objects.

**Alternatives considered**:
- Inject a `MetricsCollector` interface via DI: adds complexity (new interface, container registration, constructor changes) for no behavioral benefit. Counters don't need mocking — they're fire-and-forget.
- Decorator-based instrumentation: would require decorating every service method, harder to customize labels per call site.

## R4: Database engine wrapper

**Decision**: Replace `django.db.backends.postgresql` with `django_prometheus.db.backends.postgresql` in `DATABASES` config.

**Rationale**: Drop-in replacement. django-prometheus intercepts ORM queries and records count/duration metrics automatically. No code changes in repositories or services.

**Alternatives considered**:
- Custom database router with timing: reimplements what the wrapper already does.
- Query logging middleware: already have structured logging; metrics need numeric aggregation, not log lines.

## R5: Docker infrastructure — Prometheus + Grafana

**Decision**: Add both containers to `docker-compose.yml` (dev only). Production deployment via `compose.prod.yml` is out of scope for now.

**Rationale**:
- Dev-only keeps scope contained. Production Prometheus/Grafana typically lives on dedicated infra.
- Prometheus config: simple `prometheus.yml` with one scrape target (`ipbcb_server:8000/metrics`).
- Grafana provisioning: YAML datasource config + JSON dashboard file. No manual UI setup needed.

**Alternatives considered**:
- Managed monitoring (Datadog, New Relic): overkill for internal church app.
- Prometheus in production compose: deferred — production monitoring infra decisions are separate.

## R6: Grafana dashboard panels

**Decision**: Pre-provision a single "IPBCB Overview" dashboard with these panels:
1. Request rate (by status code) — `rate(django_http_requests_total_by_method_total[5m])`
2. Latency p50/p95/p99 — `histogram_quantile` on `django_http_requests_latency_seconds_by_view_method_bucket`
3. Error rate (4xx + 5xx) — filtered `rate(django_http_requests_total_by_method_total{status=~"4..|5.."}[5m])`
4. DB query duration — `rate(django_db_execute_total[5m])` and `histogram_quantile` on duration
5. Business counters — `rate(ipbcb_login_total[5m])`, `ipbcb_schedule_generated_total`, `ipbcb_song_plays_registered_total`

**Rationale**: Covers all spec requirements (SC-001 through SC-004). Single dashboard keeps it simple.

## R7: Metric naming conventions

**Decision**: Use `ipbcb_` prefix for all custom business metrics. Infrastructure metrics use django-prometheus defaults (`django_*`).

**Rationale**: Prometheus naming best practices require a namespace prefix to avoid collisions. `ipbcb_` matches the project name.

Custom metrics:
| Metric Name | Type | Labels |
|---|---|---|
| `ipbcb_login_total` | Counter | `result` (success/failure), `login_type` (credentials/google) |
| `ipbcb_schedule_generated_total` | Counter | — |
| `ipbcb_schedule_saved_total` | Counter | — |
| `ipbcb_song_plays_registered_total` | Counter | — |
| `ipbcb_chord_chart_views_total` | Counter | — |
| `ipbcb_lyrics_views_total` | Counter | — |
