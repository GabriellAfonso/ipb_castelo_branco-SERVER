"""Tests for core.logging.context — RequestIdFilter and ContextVar helpers."""

from __future__ import annotations

import logging

from core.logging.context import RequestIdFilter, get_request_id, set_request_id


class TestRequestIdContextVar:
    def test_default_is_none(self) -> None:
        set_request_id(None)
        assert get_request_id() is None

    def test_set_and_get(self) -> None:
        set_request_id("abc-123")
        try:
            assert get_request_id() == "abc-123"
        finally:
            set_request_id(None)

    def test_reset_to_none(self) -> None:
        set_request_id("abc-123")
        set_request_id(None)
        assert get_request_id() is None


class TestRequestIdFilter:
    def _make_record(self) -> logging.LogRecord:
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

    def test_injects_request_id_when_set(self) -> None:
        set_request_id("req-456")
        try:
            f = RequestIdFilter()
            record = self._make_record()
            result = f.filter(record)
            assert result is True
            assert record.request_id == "req-456"  # type: ignore[attr-defined]
        finally:
            set_request_id(None)

    def test_injects_none_when_unset(self) -> None:
        set_request_id(None)
        f = RequestIdFilter()
        record = self._make_record()
        f.filter(record)
        assert record.request_id is None  # type: ignore[attr-defined]

    def test_always_returns_true(self) -> None:
        """Filter should never suppress log records — only enrich them."""
        f = RequestIdFilter()
        record = self._make_record()
        assert f.filter(record) is True

    def test_outside_request_context_no_error(self) -> None:
        """Logging outside request context (management commands, startup) must not raise."""
        set_request_id(None)
        f = RequestIdFilter()
        record = self._make_record()
        f.filter(record)
        assert record.request_id is None  # type: ignore[attr-defined]
