# Quickstart: API Error Handling Validation

## Prerequisites

- Python 3.11+ with virtual environment activated
- Project dependencies installed (`pip install -r requirements.txt`)
- Database running (or use SQLite for tests)

## Run Tests

```bash
cd /workspace/backend
source wsl_venv/bin/activate
pytest server/core/tests/unit/test_exception_handler.py -v
```

## Validation Scenarios

### 1. Canonical Format on All Errors

Run the full test suite and verify no endpoint returns the old `{"error": ...}` shape:

```bash
pytest server/ -v -k "test_" --tb=short
```

Every error response in tests should contain both `error_code` and `detail` keys.

### 2. Domain Exception error_code Attributes

Verify every domain exception has `error_code`:

```bash
python -c "
from core.domain.exceptions import *
for cls in [DomainError, NotFoundError, ValidationError, ConflictError, AuthenticationError]:
    print(f'{cls.__name__}.error_code = {cls.error_code!r}')
"
```

Expected: each class prints its `error_code` value (e.g., `NOT_FOUND`, `VALIDATION_ERROR`).

### 3. Unhandled Exception Returns JSON 500

Trigger an unhandled exception in a test and verify the response:

```python
# In test: force a RuntimeError in a view, assert response is:
# {"error_code": "INTERNAL_ERROR", "detail": "An unexpected error occurred."}
# with status 500
```

### 4. Logging Verification

Run tests with log capture and verify:
- 4xx errors produce WARNING logs
- 5xx errors produce ERROR logs with traceback

```bash
pytest server/core/tests/unit/test_exception_handler.py -v --log-cli-level=DEBUG
```

### 5. No Scattered Domain Exceptions

```bash
grep -rn "class.*DomainError\|class.*NotFoundError\|class.*ValidationError\|class.*ConflictError\|class.*AuthenticationError" server/ --include="*.py" | grep -v "core/domain/exceptions.py" | grep -v "__pycache__"
```

Expected: no results (all domain exception definitions are in `core/domain/exceptions.py`).

### 6. No Manual try/except in Views

```bash
grep -rn "except.*Error" server/features/*/views/ --include="*.py" | grep -v "__pycache__"
```

Expected: no results (views delegate all error handling to centralized handler).

## Success Criteria Cross-Reference

| Scenario | Validates |
|----------|-----------|
| 1 | SC-001 (canonical format) |
| 2 | SC-006 (error_code attributes) |
| 3 | SC-001, SC-003 (500 JSON + logging) |
| 4 | SC-003 (traceback logging) |
| 5 | SC-004 (no scattered exceptions) |
| 6 | SC-005 (no view try/except) |
