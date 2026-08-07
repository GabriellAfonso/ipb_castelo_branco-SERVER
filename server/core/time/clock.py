"""Project-owned wrapper around the system clock.

Injected instead of calling ``django.utils.timezone.now()`` inline so that rules
depending on "now" — clock-skew tolerance, maximum event age — stay repeatable in
tests without patching globals.
"""

from datetime import datetime
from typing import Protocol

from django.utils import timezone


class Clock(Protocol):
    """Contract for reading the current instant."""

    def now(self) -> datetime: ...


class SystemClock:
    """Clock backed by Django's timezone-aware ``now()``.

    >>> SystemClock().now()
    datetime.datetime(2026, 8, 7, 12, 0, tzinfo=datetime.timezone.utc)
    """

    def now(self) -> datetime:
        return timezone.now()
