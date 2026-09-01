"""A dead token must reach the app in the canonical shape, like every other error."""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from conftest import make_user
from features.accounts.models.user import User

PROFILE_URL = "/api/me/profile/"


def _dead_access_token(user: User) -> str:
    """An access token the API will reject: the claim no longer matches the password."""
    token = RefreshToken.for_user(user).access_token
    del token.payload["hash_password"]
    return str(token)


@pytest.mark.django_db
def test_a_rejected_token_reports_a_recognisable_error_code() -> None:
    """Regression: SimpleJWT raises a subclass, the exact-type lookup answered UNKNOWN."""
    user = make_user(username="deadtoken", password="testpass123")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_dead_access_token(user)}")

    response = client.get(PROFILE_URL)

    assert response.status_code == 401
    assert response.data["error_code"] == "AUTHENTICATION_FAILED"


@pytest.mark.django_db
def test_the_detail_of_a_rejected_token_is_a_string() -> None:
    """Regression: it arrived as a nested object, which the app rendered as raw JSON."""
    user = make_user(username="deadtoken2", password="testpass123")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_dead_access_token(user)}")

    detail = client.get(PROFILE_URL).data["detail"]

    assert isinstance(detail, str)
    assert not detail.startswith("{")


@pytest.mark.django_db
def test_a_request_without_a_token_is_still_labelled_separately() -> None:
    """NotAuthenticated must not be swallowed by its parent once matching is by isinstance."""
    response = APIClient().get(PROFILE_URL)

    assert response.status_code == 401
    assert response.data["error_code"] == "NOT_AUTHENTICATED"
    assert response.data["detail"] == "Faça login para ter acesso."


@pytest.mark.django_db
def test_a_garbage_token_is_also_canonical() -> None:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")

    response = client.get(PROFILE_URL)

    assert response.status_code == 401
    assert response.data["error_code"] != "UNKNOWN"
    assert isinstance(response.data["detail"], str)
