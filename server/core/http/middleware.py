"""Request logging middleware.

Generates a UUID4 request_id per request, propagates it via contextvars,
and logs request start/end with timing and user context.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse
from ipware import get_client_ip

from core.logging.context import set_request_id

logger = logging.getLogger(__name__)


def _get_client_ip(request: HttpRequest) -> str:
    """Return the address nginx observed, not the one the caller claimed.

    nginx sets `X-Forwarded-For` with `$proxy_add_x_forwarded_for`, which *appends* the
    real address to whatever the client sent — so the left-most entry is attacker
    controlled and taking it made every logged IP forgeable. Right-most is the same
    resolution the axes lockout uses (AXES_IPWARE_PROXY_ORDER), so the app has one notion
    of client IP instead of two that disagree exactly when a log is worth reading.

    >>> _get_client_ip(request)
    '203.0.113.7'
    """
    client_ip: str | None
    client_ip, _ = get_client_ip(request, proxy_order="right-most")
    return client_ip or ""


def _get_user_id(request: HttpRequest) -> int | None:
    """Return authenticated user's ID, or None if anonymous."""
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        pk: int = user.pk
        return pk
    return None


class RequestLoggingMiddleware:
    """Middleware that assigns a request_id and logs request lifecycle.

    Position: second in MIDDLEWARE (after SecurityMiddleware).

    >>> m = RequestLoggingMiddleware(lambda r: HttpResponse())
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = str(uuid.uuid4())
        set_request_id(request_id)
        start_time = time.monotonic()

        try:
            logger.info(
                "Request started",
                extra={
                    "method": request.method,
                    "path": request.get_full_path(),
                    "client_ip": _get_client_ip(request),
                    "user_id": _get_user_id(request),
                },
            )

            response = self.get_response(request)

            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.get_full_path(),
                    "status_code": response.status_code,
                    "duration_ms": round((time.monotonic() - start_time) * 1000, 2),
                    "user_id": _get_user_id(request),
                },
            )

            response["X-Request-ID"] = request_id
            return response
        finally:
            set_request_id(None)
