"""Test settings — uses SQLite in-memory to avoid needing a Postgres instance."""

from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

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
    },
}
