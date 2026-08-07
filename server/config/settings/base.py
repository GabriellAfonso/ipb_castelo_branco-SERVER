"""Base Django settings.

Keep environment-specific values in dev.py/prod.py.
"""

from __future__ import annotations
import dotenv

dotenv.load_dotenv()


import os  # noqa: E402
from datetime import timedelta  # noqa: E402
from pathlib import Path  # noqa: E402


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# Core
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-ufeshinhw3=4&-^bh08^e(sn&4t=vy6=7d8b-d%o+3)#7a@jpc",
)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", default="")

DEBUG = env_bool("DJANGO_DEBUG", False)

AUTH_USER_MODEL = "accounts.User"

ALLOWED_HOSTS: list[str] = []


# Application definition
INSTALLED_APPS = [
    "django_prometheus",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Shared layer. Holds only entities used by two or more features — the church
    # service catalogue is shared by schedule and songs, which may not import each other.
    "core",
    "features.accounts",
    "features.songs",
    "features.schedule",
    "features.members",
    "features.gallery",
    "features.bible",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "core.http.middleware.RequestLoggingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", ""),
        "USER": os.environ.get("POSTGRES_USER", ""),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
]


# Auth / API
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "EXCEPTION_HANDLER": "core.http.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "500/hour",
        "user": "1000/hour",
        "login": "10/min",
        # Sized for the whole congregation behind a single church-WiFi NAT address
        # (~200 devices syncing up to 3x/hour), not for one person. See
        # specs/006-hymnal-view-history/research.md R-02.
        "hymnal_ingest": "600/hour",
    },
    # The app runs behind nginx, which sets X-Forwarded-For. Without this, DRF trusts a
    # client-supplied XFF header as the throttle key and every rate limit can be bypassed
    # by rotating it.
    "NUM_PROXIES": 1,
}


# Internationalization
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_TZ = True
USE_I18N = True


# Static/media
STATIC_URL = "/ipbcb/static/"
STATIC_ROOT = BASE_DIR / "static"

MEDIA_URL = "/ipbcb/media/"
MEDIA_ROOT = BASE_DIR / "media"


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "core.logging.context.RequestIdFilter",
        },
    },
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": "%(timestamp)s %(level)s %(name)s %(message)s",
            "rename_fields": {"levelname": "level", "name": "logger"},
            "timestamp": True,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {"level": "WARNING"},
        "django.server": {"level": "WARNING"},
        "django.db.backends": {"level": "WARNING"},
    },
}
