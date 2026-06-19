# Data Model: Application Metrics with Prometheus & Grafana

This feature introduces no new Django models or database tables. All data is held in-memory by `prometheus_client` and scraped by Prometheus into its own time-series database.

## Prometheus Metrics (in-memory)

### Auto-instrumented by django-prometheus

| Metric | Type | Labels | Source |
|---|---|---|---|
| `django_http_requests_total_by_method_total` | Counter | method, status | Middleware |
| `django_http_requests_latency_seconds_by_view_method` | Histogram | method, view | Middleware |
| `django_http_requests_body_total_bytes` | Histogram | method | Middleware |
| `django_http_responses_body_total_bytes` | Histogram | method | Middleware |
| `django_db_execute_total` | Counter | vendor, alias, type | DB engine wrapper |
| `django_db_execute_duration_seconds` | Histogram | vendor, alias | DB engine wrapper |
| `django_db_errors_total` | Counter | vendor, alias, type | DB engine wrapper |

### Custom business metrics (core/metrics.py)

| Metric | Type | Labels | Instrumented In |
|---|---|---|---|
| `ipbcb_login_total` | Counter | result, login_type | LoginService, GoogleAuthService |
| `ipbcb_schedule_generated_total` | Counter | — | MonthlyScheduler |
| `ipbcb_schedule_saved_total` | Counter | — | Schedule save service |
| `ipbcb_song_plays_registered_total` | Counter | — | RegisterPlaysService |
| `ipbcb_chord_chart_views_total` | Counter | — | SongService |
| `ipbcb_lyrics_views_total` | Counter | — | SongService |

## External Data Stores

### Prometheus (container)

- Time-series database storing scraped metrics
- Retention: default 15 days (configurable)
- Scrape interval: 15 seconds
- Storage: Docker volume (`ipbcb_prometheus_data`)

### Grafana (container)

- Dashboard definitions stored in provisioned JSON files
- Datasource config via YAML provisioning
- Storage: Docker volume (`ipbcb_grafana_data`)
- No persistent user data — dashboards are code-provisioned

## Entity Relationships

```
Django App (ipbcb_server)
  └── /metrics endpoint
        └── prometheus_client registry (in-memory)
              ├── django-prometheus auto metrics
              └── custom ipbcb_* metrics

Prometheus (container)
  └── scrapes /metrics every 15s
        └── stores time-series data

Grafana (container)
  └── queries Prometheus
        └── renders dashboard panels
```
