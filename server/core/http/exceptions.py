import logging

from django.conf import settings
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    ValidationError as DRFValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_DOMAIN_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    ConflictError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
}


def _status_for_domain(exc: DomainError) -> int:
    for cls, http_status in _DOMAIN_STATUS_MAP.items():
        if isinstance(exc, cls):
            return http_status
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _build_canonical(
    error_code: str,
    detail: str,
    field_errors: dict[str, list[str]] | None = None,
    **extra: object,
) -> dict[str, object]:
    body: dict[str, object] = {"error_code": error_code, "detail": detail}
    if field_errors:
        body["field_errors"] = field_errors
    body.update(extra)
    return body


def _handle_domain_exception(exc: DomainError) -> Response:
    http_status = _status_for_domain(exc)
    body = _build_canonical(exc.error_code, str(exc))
    body.update(exc.extra_context())
    return Response(body, status=http_status)


def _reshape_drf_validation(response: Response) -> Response:
    """Convert DRF ValidationError response.data into canonical format."""
    data = response.data

    if isinstance(data, dict):
        # Field-level errors: {"field": ["msg", ...]}
        field_errors = {k: v if isinstance(v, list) else [v] for k, v in data.items()}
        body = _build_canonical("VALIDATION_ERROR", "Validation failed.", field_errors=field_errors)
    elif isinstance(data, list):
        body = _build_canonical("VALIDATION_ERROR", " ".join(str(e) for e in data))
    else:
        body = _build_canonical("VALIDATION_ERROR", str(data))

    response.data = body
    return response


_DRF_ERROR_CODE_MAP: dict[type[Exception], str] = {
    NotAuthenticated: "NOT_AUTHENTICATED",
    AuthenticationFailed: "AUTHENTICATION_FAILED",
    PermissionDenied: "PERMISSION_DENIED",
    Throttled: "THROTTLED",
}

_DRF_DETAIL_OVERRIDES: dict[type[Exception], str] = {
    NotAuthenticated: "Faça login para ter acesso.",
    AuthenticationFailed: "Token inválido ou expirado. Faça login novamente.",
}


def _reshape_drf_exception(exc: Exception, response: Response) -> Response:
    if isinstance(exc, DRFValidationError):
        return _reshape_drf_validation(response)

    error_code = _DRF_ERROR_CODE_MAP.get(type(exc), "UNKNOWN")
    detail = _DRF_DETAIL_OVERRIDES.get(type(exc))

    if detail is None:
        detail = str(getattr(exc, "detail", "An error occurred."))

    response.data = _build_canonical(error_code, detail)
    return response


def _handle_pydantic_validation(exc: PydanticValidationError) -> Response:
    field_errors: dict[str, list[str]] = {}
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"])
        field_errors.setdefault(loc, []).append(err["msg"])
    body = _build_canonical("VALIDATION_ERROR", "Validation failed.", field_errors=field_errors)
    return Response(body, status=status.HTTP_400_BAD_REQUEST)


def _log_response(exc: Exception, response: Response) -> None:
    if response.status_code >= 500:
        logger.error(
            "Server error %s: %s",
            response.data.get("error_code", "UNKNOWN"),
            response.data.get("detail", ""),
            exc_info=exc,
        )
    else:
        logger.warning(
            "Client error %s %s: %s",
            response.status_code,
            response.data.get("error_code", "UNKNOWN"),
            response.data.get("detail", ""),
        )


def custom_exception_handler(exc: Exception, context: dict[str, object]) -> Response:
    # 1. Domain exceptions
    if isinstance(exc, DomainError):
        response = _handle_domain_exception(exc)
        _log_response(exc, response)
        return response

    # 2. Pydantic validation errors (safety net for unhandled Pydantic errors)
    if isinstance(exc, PydanticValidationError):
        response = _handle_pydantic_validation(exc)
        _log_response(exc, response)
        return response

    # 3. DRF-known exceptions
    drf_response = exception_handler(exc, context)
    if drf_response is not None:
        response = drf_response
        response = _reshape_drf_exception(exc, response)
        _log_response(exc, response)
        return response

    # 4. Unhandled exceptions — structured 500, never None
    detail = str(exc) if settings.DEBUG else "An unexpected error occurred."
    body = _build_canonical("INTERNAL_ERROR", detail)
    response = Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    _log_response(exc, response)
    return response
