from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, object]) -> Response | None:
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
