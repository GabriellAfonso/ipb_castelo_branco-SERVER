# Contract: /metrics Endpoint

## Endpoint

```
GET /metrics
```

**Authentication**: None (unauthenticated)
**Content-Type**: `text/plain; version=0.0.4; charset=utf-8` (Prometheus exposition format)

## Routing

- Accessible at root level: `http://<host>:8000/metrics`
- NOT behind `/ipbcb/` prefix
- Same level as `/health/` endpoint

## Response Format

Standard Prometheus exposition format. Example excerpt:

```
# HELP django_http_requests_total_by_method_total Count of requests by method.
# TYPE django_http_requests_total_by_method_total counter
django_http_requests_total_by_method_total{method="GET",status="200"} 42.0

# HELP ipbcb_login_total Total login attempts.
# TYPE ipbcb_login_total counter
ipbcb_login_total{login_type="credentials",result="success"} 10.0
ipbcb_login_total{login_type="google",result="success"} 5.0
ipbcb_login_total{login_type="credentials",result="failure"} 2.0
```

## Status Codes

| Code | Condition |
|------|-----------|
| 200 | Metrics returned successfully |
| 500 | Internal error in metrics collection (should not happen) |

## Scrape Configuration

Prometheus scrapes this endpoint at 15-second intervals from within the Docker network:

```yaml
scrape_configs:
  - job_name: "django"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["ipbcb_server:8000"]
```
