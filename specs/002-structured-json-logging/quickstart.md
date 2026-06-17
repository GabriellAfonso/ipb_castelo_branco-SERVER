# Quickstart: Validate Structured JSON Logging

## Prerequisites

- Docker environment running (or local dev with `python manage.py runserver`)
- `python-json-logger` installed (`pip install python-json-logger`)
- Middleware registered in `MIDDLEWARE` setting
- `LOGGING` configuration added to `settings/base.py`

## Validation Scenarios

### 1. Verify JSON log output

```bash
# Make a request and check stdout
curl -s -D- http://localhost:8000/ipbcb/api/health/

# Expected: stdout shows JSON log lines, response includes X-Request-ID header
# X-Request-ID: <uuid4>
```

Parse log output with `jq`:
```bash
docker logs <container> 2>&1 | tail -1 | jq .
# Should parse without errors — valid JSON
```

### 2. Verify request_id correlation

```bash
# Capture the request ID from response header
REQUEST_ID=$(curl -s -D- http://localhost:8000/ipbcb/api/songs/ 2>&1 | grep -i x-request-id | awk '{print $2}' | tr -d '\r')

# Search logs for that request ID
docker logs <container> 2>&1 | grep "$REQUEST_ID"
# Expected: at least 2 lines (request start + request end) with matching request_id
```

### 3. Verify error traceability

```bash
# Trigger a 404
curl -s http://localhost:8000/ipbcb/api/songs/99999/

# Check logs — should see WARNING level JSON with request_id and error details
docker logs <container> 2>&1 | tail -3 | jq .
```

### 4. Verify request duration tracking

```bash
# Check that duration_ms appears in completion log
docker logs <container> 2>&1 | jq 'select(.message == "Request completed") | .duration_ms'
# Expected: positive number (e.g., 12.5)
```

### 5. Run automated tests

```bash
source wsl_venv/bin/activate
pytest server/core/tests/unit/test_request_logging_middleware.py -v
pytest server/core/tests/unit/test_json_logging.py -v
```

## Expected Log Structure

See [contracts/log-format.md](contracts/log-format.md) for the complete JSON schema and examples.

## Checklist

- [ ] All log lines are valid JSON (parseable by `jq`)
- [ ] `X-Request-ID` header present on every response
- [ ] Request start log has: method, path, client_ip
- [ ] Request end log has: method, path, status_code, duration_ms
- [ ] Exception handler logs include request_id automatically
- [ ] Logs outside request context (startup, management commands) work without errors
