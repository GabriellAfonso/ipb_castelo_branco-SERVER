"""The refresh endpoint must hand back credentials the API will actually accept.

Regression for a deploy-blocking defect: SimpleJWT's TokenRefreshView copies the presented
token's claims into the new access token. A token minted before ``CHECK_REVOKE_TOKEN``
existed therefore refreshed into another token missing ``hash_password`` — the endpoint
answered 200, the app stored the new token, every request kept failing 401, and the app's
TokenAuthenticator never cleared storage (it only clears when the *refresh* fails). The
member was stuck with no route back to the login screen.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from conftest import get_refresh_token, make_user
from features.accounts.models.user import User

REFRESH_URL = "/api/auth/refresh/"
PROFILE_URL = "/api/me/profile/"


def _token_minted_before_the_claim_existed(user: User) -> str:
    refresh = RefreshToken.for_user(user)
    del refresh.payload["hash_password"]
    return str(refresh)


@pytest.mark.django_db
def test_refreshing_a_pre_claim_token_returns_a_usable_access_token() -> None:
    user = make_user(username="predeploy", password="testpass123")
    client = APIClient()

    response = client.post(
        REFRESH_URL, {"refresh": _token_minted_before_the_claim_existed(user)}, format="json"
    )
    assert response.status_code == 200

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    assert client.get(PROFILE_URL).status_code == 200


@pytest.mark.django_db
def test_the_rotated_refresh_token_is_also_usable() -> None:
    """The pair must both be current — otherwise the next refresh reopens the loop."""
    user = make_user(username="predeploy2", password="testpass123")
    client = APIClient()

    first = client.post(
        REFRESH_URL, {"refresh": _token_minted_before_the_claim_existed(user)}, format="json"
    )
    second = client.post(REFRESH_URL, {"refresh": first.data["refresh"]}, format="json")

    assert second.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {second.data['access']}")
    assert client.get(PROFILE_URL).status_code == 200


@pytest.mark.django_db
def test_a_current_token_still_refreshes() -> None:
    user = make_user(username="current", password="testpass123")

    response = APIClient().post(REFRESH_URL, {"refresh": get_refresh_token(user)}, format="json")

    assert response.status_code == 200
    assert "access" in response.data and "refresh" in response.data


@pytest.mark.django_db
def test_the_presented_token_is_single_use() -> None:
    """Rotation still blacklists what was handed in."""
    user = make_user(username="rotating", password="testpass123")
    refresh = get_refresh_token(user)
    client = APIClient()
    client.post(REFRESH_URL, {"refresh": refresh}, format="json")

    assert client.post(REFRESH_URL, {"refresh": refresh}, format="json").status_code == 401


@pytest.mark.django_db
def test_an_inactive_user_cannot_refresh() -> None:
    """Otherwise the endpoint mints a token JWTAuthentication immediately rejects."""
    user = make_user(username="disabled", password="testpass123")
    refresh = get_refresh_token(user)
    user.is_active = False
    user.save()

    assert APIClient().post(REFRESH_URL, {"refresh": refresh}, format="json").status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("body", [{}, {"refresh": ""}, {"refresh": "garbage"}, ["x"]])
def test_malformed_refresh_requests_are_refused(body: object) -> None:
    response = APIClient().post(REFRESH_URL, body, format="json")

    assert response.status_code in (400, 401)
    assert response.data["error_code"] != "UNKNOWN"
