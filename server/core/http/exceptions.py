from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)


def custom_exception_handler(exc: Exception, context: dict[str, object]) -> Response | None:
    # Handle domain exceptions before DRF's handler (which only knows DRF exceptions)
    if isinstance(exc, DomainError):
        return _handle_domain_exception(exc)

    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, NotAuthenticated):
        response.data = {"detail": "Faça login para ter acesso."}
    elif isinstance(exc, AuthenticationFailed):
        response.data = {"detail": "Token inválido ou expirado. Faça login novamente."}
    elif isinstance(exc, PermissionDenied):
        response.data = {"detail": exc.detail if hasattr(exc, "detail") else "Acesso restrito."}

    return response


def _handle_domain_exception(exc: DomainError) -> Response:
    if isinstance(exc, NotFoundError):
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, ValidationError):
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, ConflictError):
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    if isinstance(exc, AuthenticationError):
        return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
