import pytest
from django.http import HttpRequest
from django.test import RequestFactory

from core.application.dtos.auth_dtos import LoginDTO, TokenDTO
from core.domain.exceptions import InvalidCredentialsError
from features.accounts.services.login_service import LoginService


@pytest.fixture
def service() -> LoginService:
    return LoginService()


@pytest.fixture
def request_() -> HttpRequest:
    """The request django-axes needs to attribute the attempt to a client (plan D-1)."""
    return RequestFactory().post("/api/auth/login/")


@pytest.fixture
def sample_dto() -> LoginDTO:
    return LoginDTO(username="testuser", password="testpass123")


@pytest.mark.django_db
def test_login_success(service: LoginService, request_: HttpRequest) -> None:
    from features.accounts.models.user import User

    user = User.objects.create_user(username="testuser", password="testpass123")  # noqa: F841
    dto = LoginDTO(username="testuser", password="testpass123")

    result = service.login(dto, request_)

    assert isinstance(result, TokenDTO)
    assert result.access
    assert result.refresh


@pytest.mark.django_db
def test_login_invalid_credentials_raises(
    service: LoginService, sample_dto: LoginDTO, request_: HttpRequest
) -> None:
    with pytest.raises(InvalidCredentialsError):
        service.login(sample_dto, request_)


@pytest.mark.django_db
def test_login_wrong_password_raises(service: LoginService, request_: HttpRequest) -> None:
    from features.accounts.models.user import User

    User.objects.create_user(username="testuser", password="correctpass")
    dto = LoginDTO(username="testuser", password="wrongpass")

    with pytest.raises(InvalidCredentialsError):
        service.login(dto, request_)
