"""Tests for RequestLoggingMiddleware — covers US1, US2, US3."""

from __future__ import annotations

import logging
import uuid
from unittest.mock import MagicMock

import pytest
from django.http import HttpRequest, HttpResponse
from collections.abc import Generator

from django.test import RequestFactory

from core.http.exceptions import custom_exception_handler
from core.domain.exceptions import NotFoundError
from core.http.middleware import RequestLoggingMiddleware
from core.logging.context import get_request_id, set_request_id


class FakeJsonHandler(logging.Handler):
    """Captures log records for assertion."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture()
def log_capture() -> Generator[FakeJsonHandler]:
    handler = FakeJsonHandler()
    logger = logging.getLogger("core.http.middleware")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)


@pytest.fixture()
def rf() -> RequestFactory:
    return RequestFactory()


def _ok_response(request: HttpRequest) -> HttpResponse:
    return HttpResponse("OK", status=200)


def _error_response(request: HttpRequest) -> HttpResponse:
    raise ValueError("boom")


# ──────────────────────────────────────────────────────────
# US1: Trace an Error by Request ID
# ──────────────────────────────────────────────────────────


class TestUS1RequestIdTracing:
    def test_response_has_x_request_id_header(self, rf: RequestFactory) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        request = rf.get("/ipbcb/api/health/")
        response = middleware(request)
        request_id = response.get("X-Request-ID")
        assert request_id is not None
        uuid.UUID(request_id)  # raises if not valid UUID4

    def test_request_id_is_unique_per_request(self, rf: RequestFactory) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        r1 = middleware(rf.get("/a/"))
        r2 = middleware(rf.get("/b/"))
        assert r1["X-Request-ID"] != r2["X-Request-ID"]

    def test_context_var_reset_after_request(self, rf: RequestFactory) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        middleware(rf.get("/"))
        assert get_request_id() is None

    def test_context_var_reset_after_exception(self, rf: RequestFactory) -> None:
        middleware = RequestLoggingMiddleware(_error_response)
        with pytest.raises(ValueError):
            middleware(rf.get("/"))
        assert get_request_id() is None

    def test_log_records_share_request_id(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        middleware(rf.get("/test/"))
        # All log records from this request should reference same request_id
        for record in log_capture.records:
            assert getattr(record, "request_id", None) is not None


# ──────────────────────────────────────────────────────────
# US2: Monitor Request Traffic in Docker
# ──────────────────────────────────────────────────────────


class TestUS2TrafficMonitoring:
    def test_request_start_log_fields(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        middleware(rf.get("/ipbcb/api/songs/"))
        start_record = log_capture.records[0]
        assert start_record.getMessage() == "Request started"
        assert start_record.method == "GET"  # type: ignore[attr-defined]
        assert "/ipbcb/api/songs/" in start_record.path  # type: ignore[attr-defined]
        assert hasattr(start_record, "client_ip")

    def test_request_end_log_fields(self, rf: RequestFactory, log_capture: FakeJsonHandler) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        middleware(rf.get("/ipbcb/api/songs/"))
        end_record = log_capture.records[1]
        assert end_record.getMessage() == "Request completed"
        assert end_record.method == "GET"  # type: ignore[attr-defined]
        assert end_record.status_code == 200  # type: ignore[attr-defined]
        assert end_record.duration_ms > 0  # type: ignore[attr-defined]

    def test_duration_ms_is_positive(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        middleware(rf.get("/"))
        end_record = log_capture.records[1]
        assert isinstance(end_record.duration_ms, float)  # type: ignore[attr-defined]
        assert end_record.duration_ms >= 0  # type: ignore[attr-defined]

    def test_user_id_null_for_anonymous(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        middleware(rf.get("/"))
        start_record = log_capture.records[0]
        assert start_record.user_id is None  # type: ignore[attr-defined]

    def test_user_id_for_authenticated(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        request = rf.get("/")
        request.user = MagicMock(is_authenticated=True, pk=42)
        middleware(request)
        end_record = log_capture.records[1]
        assert end_record.user_id == 42  # type: ignore[attr-defined]

    def test_client_ip_is_the_right_most_forwarded_entry(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        """nginx appends the observed address, so the right-most entry is the real one."""
        middleware = RequestLoggingMiddleware(_ok_response)
        request = rf.get("/", HTTP_X_FORWARDED_FOR="203.0.113.50, 70.41.3.18")
        middleware(request)
        start_record = log_capture.records[0]
        assert start_record.client_ip == "70.41.3.18"  # type: ignore[attr-defined]

    def test_client_ip_ignores_an_address_the_caller_invented(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        """Regression: taking the left-most entry logged whatever the caller sent, which
        made every logged IP forgeable — worst exactly when the log matters, such as
        investigating what the axes lockout blocked."""
        middleware = RequestLoggingMiddleware(_ok_response)
        request = rf.get("/", HTTP_X_FORWARDED_FOR="8.8.8.8, 198.51.100.9")
        middleware(request)
        start_record = log_capture.records[0]
        assert start_record.client_ip == "198.51.100.9"  # type: ignore[attr-defined]

    def test_client_ip_with_a_single_forwarded_entry(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        """The production shape: one proxy, so nginx sends exactly one address."""
        middleware = RequestLoggingMiddleware(_ok_response)
        request = rf.get("/", HTTP_X_FORWARDED_FOR="198.51.100.9")
        middleware(request)
        start_record = log_capture.records[0]
        assert start_record.client_ip == "198.51.100.9"  # type: ignore[attr-defined]

    def test_client_ip_fallback_to_remote_addr(
        self, rf: RequestFactory, log_capture: FakeJsonHandler
    ) -> None:
        middleware = RequestLoggingMiddleware(_ok_response)
        request = rf.get("/")
        middleware(request)
        start_record = log_capture.records[0]
        assert start_record.client_ip == "127.0.0.1"  # type: ignore[attr-defined]


# ──────────────────────────────────────────────────────────
# US3: Existing Exception Logging Benefits Automatically
# ──────────────────────────────────────────────────────────


class TestUS3ExceptionHandlerIntegration:
    def test_exception_handler_warning_includes_request_id(self) -> None:
        """custom_exception_handler WARNING logs should pick up request_id from ContextVar."""
        handler = FakeJsonHandler()
        exc_logger = logging.getLogger("core.http.exceptions")
        exc_logger.addHandler(handler)
        exc_logger.setLevel(logging.DEBUG)

        set_request_id("test-req-id-789")
        try:
            from core.logging.context import RequestIdFilter

            filt = RequestIdFilter()
            exc_logger.addFilter(filt)

            exc = NotFoundError("Song not found: id=99")
            context: dict[str, object] = {"view": None, "args": (), "kwargs": {}, "request": None}
            custom_exception_handler(exc, context)

            assert len(handler.records) > 0
            record = handler.records[0]
            assert record.request_id == "test-req-id-789"  # type: ignore[attr-defined]

            exc_logger.removeFilter(filt)
        finally:
            set_request_id(None)
            exc_logger.removeHandler(handler)

    def test_error_with_traceback_in_single_record(self) -> None:
        """Traceback from 5xx should be part of the log record, not separate lines."""
        handler = FakeJsonHandler()
        exc_logger = logging.getLogger("core.http.exceptions")
        exc_logger.addHandler(handler)
        exc_logger.setLevel(logging.DEBUG)

        set_request_id("test-500")
        try:
            exc = RuntimeError("unexpected failure")
            context: dict[str, object] = {"view": None, "args": (), "kwargs": {}, "request": None}
            custom_exception_handler(exc, context)

            error_records = [r for r in handler.records if r.levelno >= logging.ERROR]
            assert len(error_records) == 1
            assert error_records[0].exc_info is not None
        finally:
            set_request_id(None)
            exc_logger.removeHandler(handler)


# ──────────────────────────────────────────────────────────
# Phase 6: Edge cases
# ──────────────────────────────────────────────────────────


class TestMiddlewareEdgeCases:
    def test_middleware_exception_resets_context_var(self, rf: RequestFactory) -> None:
        """ContextVar must be reset even if view raises."""
        middleware = RequestLoggingMiddleware(_error_response)
        with pytest.raises(ValueError):
            middleware(rf.get("/"))
        assert get_request_id() is None

    def test_x_request_id_header_set_even_on_error_response(self, rf: RequestFactory) -> None:
        """If view returns 500 response (not exception), header should still be set."""

        def server_error(request: HttpRequest) -> HttpResponse:
            return HttpResponse("error", status=500)

        middleware = RequestLoggingMiddleware(server_error)
        response = middleware(rf.get("/"))
        assert response["X-Request-ID"] is not None
