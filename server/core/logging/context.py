"""Request-scoped logging context using contextvars.

Provides a ContextVar holding the current request_id and a logging.Filter
that injects it into every log record automatically.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str | None) -> None:
    """Set the request_id for the current context."""
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    """Get the request_id for the current context.

    Returns None when called outside a request lifecycle.

    >>> set_request_id("abc-123")
    >>> get_request_id()
    'abc-123'
    """
    return _request_id_var.get()


class RequestIdFilter(logging.Filter):
    """Logging filter that injects request_id into every log record.

    Reads from the ContextVar — returns None when outside request context,
    so management commands and startup logs work without errors.

    >>> f = RequestIdFilter()
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True
