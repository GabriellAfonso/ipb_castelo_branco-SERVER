from unittest.mock import MagicMock

from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied

from core.http.exceptions import custom_exception_handler


def _context() -> dict[str, object]:
    return {"request": MagicMock(), "view": MagicMock()}


def test_not_authenticated_returns_custom_message() -> None:
    response = custom_exception_handler(NotAuthenticated(), _context())
    assert response is not None
    assert response.data["detail"] == "Faça login para ter acesso."


def test_authentication_failed_returns_custom_message() -> None:
    response = custom_exception_handler(AuthenticationFailed(), _context())
    assert response is not None
    assert response.data["detail"] == "Token inválido ou expirado. Faça login novamente."


def test_permission_denied_uses_exc_detail() -> None:
    exc = PermissionDenied(detail="Disponível apenas para membros.")
    response = custom_exception_handler(exc, _context())
    assert response is not None
    assert response.data["detail"] == "Disponível apenas para membros."


def test_permission_denied_generic_fallback() -> None:
    response = custom_exception_handler(PermissionDenied(), _context())
    assert response is not None
    assert "detail" in response.data


def test_unhandled_exception_returns_none() -> None:
    response = custom_exception_handler(ValueError("boom"), _context())
    assert response is None
