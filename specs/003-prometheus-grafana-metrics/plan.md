# Implementation Plan: Application Metrics with Prometheus & Grafana

**Branch**: `003-prometheus-grafana-metrics` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-prometheus-grafana-metrics/spec.md`

## Summary

Add observability to the Django API via `django-prometheus` for auto-instrumented RED and database metrics, custom `prometheus_client` counters for business events in the service layer, a Prometheus container for scraping, and a Grafana container with a provisioned dashboard. The `/metrics` endpoint lives at root level (not behind `/ipbcb/`), unauthenticated, accessible only within the Docker network.

## Technical Context

**Language/Version**: Python 3.x, Django 6.0.3

**Primary Dependencies**: django-prometheus (wraps prometheus_client), djangorestframework 3.16.1, dependency-injector 4.48.3

**Storage**: PostgreSQL 16 (via psycopg2-binary)

**Testing**: pytest + pytest-django

**Target Platform**: Linux server (Docker containers)

**Project Type**: Web service (REST API for Android app)

**Performance Goals**: Metrics collection must add no perceptible latency. `/metrics` endpoint scrape < 500ms.

**Constraints**: `/metrics` must NOT be behind `/ipbcb/` prefix. Business metrics in service layer only (clean architecture). No changes to existing logging or exception handling.

**Scale/Scope**: Small internal church app. Single Prometheus + Grafana instance. ~10 custom business counters.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Rule | Status | Notes |
|------|--------|-------|
| Auth: protected endpoints require JWT/OAuth | PASS | `/metrics` is intentionally unauthenticated — same pattern as `/health/` and OpenAPI schema (accepted risk for internal app) |
| Architecture: views never access repositories | PASS | Metrics endpoint is a thin passthrough to prometheus_client; no repo access |
| Architecture: services never import HTTP objects | PASS | Business metrics use prometheus_client directly, no HTTP imports |
| Architecture: dependencies injected via container | PASS | Metrics registry is a module-level singleton (prometheus_client design); services receive no new constructor deps |
| Security: no hardcoded credentials | PASS | No secrets involved |
| Code: all code in English | PASS | |
| Deployment: base path /ipbcb/ behind nginx | PASS | `/metrics` explicitly outside this prefix per spec FR-003 |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-prometheus-grafana-metrics/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
server/
├── config/
│   ├── settings/
│   │   ├── base.py              # MODIFIED: add django_prometheus to INSTALLED_APPS, MIDDLEWARE, DATABASES engine
│   │   └── prod.py              # MODIFIED: same changes for production
│   ├── urls.py                  # MODIFIED: add /metrics endpoint
│   └── di.py                    # NO CHANGE (metrics use module-level registry, not DI)
├── core/
│   ├── metrics.py               # NEW: custom business metric definitions (counters/histograms)
│   ├── http/
│   │   └── middleware.py        # NO CHANGE
│   └── logging/
│       └── context.py           # NO CHANGE
└── features/
    ├── accounts/services/
    │   ├── login_service.py     # MODIFIED: increment login counter on success/failure
    │   └── google_auth_service.py  # MODIFIED: increment login counter on success/failure
    ├── songs/services/
    │   ├── song_service.py      # MODIFIED: increment chord chart / lyrics view counters
    │   └── register_plays_service.py  # MODIFIED: increment play registration counter
    └── schedule/services/
        └── monthly_scheduler.py # MODIFIED: increment schedule generation counter

docker-compose.yml               # MODIFIED: add prometheus + grafana services
monitoring/                       # NEW: infrastructure config directory
├── prometheus/
│   └── prometheus.yml           # Prometheus scrape config
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml   # Auto-configure Prometheus datasource
    │   └── dashboards/
    │       └── dashboard.yml    # Dashboard provisioning config
    └── dashboards/
        └── ipbcb-overview.json  # Pre-built Grafana dashboard
```

**Structure Decision**: New files follow existing project layout. `core/metrics.py` sits alongside `core/logging/` as shared infrastructure. `monitoring/` at repo root for Docker infra config (not inside `server/` since it's not Django code).
