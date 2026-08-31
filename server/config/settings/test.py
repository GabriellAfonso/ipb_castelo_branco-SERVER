"""Test settings — uses SQLite in-memory to avoid needing a Postgres instance."""

from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

# base.py has no fallback key, so the suite supplies its own.
# At least 32 bytes: PyJWT warns below that for HS256 (RFC 7518 §3.2).
SECRET_KEY = "insecure-test-only-key-with-enough-bytes-for-hs256"  # nosec B105
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": SECRET_KEY}  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable secure cookies for tests
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Disable throttling in tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "99999/min",
        "user": "99999/min",
        "login": "99999/min",
        # Views that declare throttle_classes explicitly (hymnal ingest) keep throttling
        # even when DEFAULT_THROTTLE_CLASSES is empty, so the scope must exist here.
        "hymnal_ingest": "99999/min",
    },
}
