"""Token revocation: logout blacklists a refresh token, and a password change kills all."""

import pytest
from rest_framework.test import APIClient

from conftest import get_refresh_token, make_auth_client, make_user

LOGOUT_URL = "/api/auth/logout/"
REFRESH_URL = "/api/auth/refresh/"
PROFILE_URL = "/api/me/profile/"


@pytest.mark.django_db
def test_logout_blacklists_the_refresh_token() -> None:
    user = make_user(username="logoutuser", password="testpass123")
    refresh = get_refresh_token(user)

    response = APIClient().post(LOGOUT_URL, {"refresh": refresh}, format="json")

    assert response.status_code == 200


@pytest.mark.django_db
def test_a_blacklisted_refresh_token_cannot_be_used_again() -> None:
    """Regression: without the route, a leaked refresh token stayed usable for 30 days."""
    user = make_user(username="blacklisted", password="testpass123")
    refresh = get_refresh_token(user)
    client = APIClient()
    client.post(LOGOUT_URL, {"refresh": refresh}, format="json")

    response = client.post(REFRESH_URL, {"refresh": refresh}, format="json")

    assert response.status_code == 401


@pytest.mark.django_db
def test_logout_rejects_a_malformed_token() -> None:
    response = APIClient().post(LOGOUT_URL, {"refresh": "not-a-token"}, format="json")

    assert response.status_code == 401


@pytest.mark.django_db
def test_changing_the_password_revokes_tokens_already_issued() -> None:
    """CHECK_REVOKE_TOKEN: the fix for a stolen device, without disabling the account."""
    user = make_user(username="rotated", password="testpass123")
    client = make_auth_client(user)
    assert client.get(PROFILE_URL).status_code == 200

    user.set_password("a-brand-new-password")
    user.save()

    assert client.get(PROFILE_URL).status_code == 401


@pytest.mark.django_db
def test_deactivating_the_user_still_revokes_access() -> None:
    """CHECK_USER_IS_ACTIVE is on by default; this pins the behaviour."""
    user = make_user(username="deactivated", password="testpass123")
    client = make_auth_client(user)

    user.is_active = False
    user.save()

    assert client.get(PROFILE_URL).status_code == 401
