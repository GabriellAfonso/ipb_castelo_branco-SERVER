# Quickstart: Validating Application Metrics

## Prerequisites

- Docker and docker-compose installed
- Project `.env` file configured (see `.env.example`)

## 1. Start All Services

```bash
docker-compose up --build -d
```

Expected: `ipbcb_server`, `ipbcb_db`, `prometheus`, and `grafana` containers running.

```bash
docker-compose ps
```

## 2. Verify /metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

**Expected**: Prometheus exposition format text containing:
- `django_http_requests_total_by_method_total` (counter)
- `django_http_requests_latency_seconds_by_view_method_bucket` (histogram)
- `django_db_execute_total` (counter)
- `ipbcb_login_total` (counter, may be 0)

## 3. Generate Traffic for Business Metrics

```bash
# Login to generate login metrics
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}'

# Check metrics again
curl http://localhost:8000/metrics | grep ipbcb_
```

**Expected**: `ipbcb_login_total{login_type="credentials",result="..."}` counter incremented.

## 4. Verify Prometheus Scraping

```bash
# Open Prometheus UI
# Navigate to: http://localhost:9090

# Check targets are UP
# Navigate to: http://localhost:9090/targets
```

**Expected**: Target `django` shows status `UP` with last scrape < 15s ago.

```bash
# Query a metric
curl 'http://localhost:9090/api/v1/query?query=django_http_requests_total_by_method_total'
```

**Expected**: JSON response with metric data.

## 5. Verify Grafana Dashboard

```bash
# Open Grafana UI
# Navigate to: http://localhost:3000
# Default credentials: admin / admin
```

**Expected**:
1. Prometheus datasource pre-configured (Settings > Data Sources)
2. "IPBCB Overview" dashboard available (Dashboards > Browse)
3. Dashboard panels showing: request rate, latency percentiles, error rate, DB query duration, business counters

## 6. Verify No Impact on Existing Functionality

```bash
# Health check still works
curl http://localhost:8000/health/

# API schema still works
curl http://localhost:8000/api/schema/

# Structured JSON logging still present in container logs
docker-compose logs ipbcb_server --tail 10
```

**Expected**: All existing endpoints work. Logs still in structured JSON format with `request_id`.

## Validation Checklist

- [ ] `/metrics` returns Prometheus format data (200, no auth required)
- [ ] RED metrics present: request count, latency histogram, error count
- [ ] DB metrics present: query count, duration
- [ ] Business metrics present after traffic: `ipbcb_login_total`, `ipbcb_schedule_generated_total`, etc.
- [ ] Prometheus target shows UP
- [ ] Grafana dashboard loads with data
- [ ] Existing API endpoints unaffected
- [ ] Structured JSON logging unchanged
