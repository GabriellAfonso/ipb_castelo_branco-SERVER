"""Production settings."""

from __future__ import annotations

import os
from config.settings.base import *  # noqa: F403

# ─── Sentry — error tracking (only if DSN is configured) ────────────────────
_sentry_dsn = os.environ.get("SENTRY_DSN", "")
if _sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(
        dsn=_sentry_dsn,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

FORCE_SCRIPT_NAME = "/ipbcb"
USE_X_FORWARDED_HOST = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


def _require_csv_env(name: str) -> list[str]:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return [part.strip() for part in value.split(",") if part.strip()]


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]

ALLOWED_HOSTS = _require_csv_env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = _require_csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")

CSRF_COOKIE_PATH = "/ipbcb/"
SESSION_COOKIE_PATH = "/ipbcb/"

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# ─── API Docs — correct public server prefix behind nginx reverse proxy ────
# nginx strips /ipbcb before forwarding to Django, so Swagger UI must know
# the real public base to build "Try it out" request URLs correctly.
SPECTACULAR_SETTINGS = {
    "SERVERS": [{"url": "/ipbcb", "description": "Production"}],
}
