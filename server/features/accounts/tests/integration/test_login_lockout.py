"""Failed-login lockout, end to end. See specs/008-login-brute-force-lockout/spec.md.

``AXES_ENABLED`` is off in the test settings (D-7), so every test here turns it on
explicitly. Each also clears the attempt table it fills, because the records live in the
database and a leaked lockout would fail an unrelated test later in the run.
"""

import json
from collections.abc import Iterator

import pytest
from axes.models import AccessAttempt
from django.http import HttpResponse
from django.test import Client, override_settings
from rest_framework.test import APIClient

from conftest import make_user
from core.http.lockout import ACCOUNT_LOCKED_ERROR_CODE

LOGIN_URL = "/api/auth/login/"
ADMIN_LOGIN_URL = "/admin/login/"

FAILURE_LIMIT = 5
CHURCH_WIFI = "198.51.100.10"
OTHER_ADDRESS = "203.0.113.99"

PASSWORD = "correct-password"  # nosec B105
WRONG_PASSWORD = "wrong-password"  # nosec B105

axes_on = override_settings(AXES_ENABLED=True)


@pytest.fixture(autouse=True)
def clear_attempts() -> Iterator[None]:
    """Attempts are rows, not process state — they outlive the test that created them."""
    yield
    AccessAttempt.objects.all().delete()


def _login(client: APIClient, username: str, password: str, address: str) -> HttpResponse:
    return client.post(
        LOGIN_URL,
        {"username": username, "password": password},
        format="json",
        REMOTE_ADDR=address,
    )


def _fail_until_locked(client: APIClient, username: str, address: str) -> None:
    """Spend the whole budget. The last of these is already answered with the lockout."""
    for _ in range(FAILURE_LIMIT):
        _login(client, username, WRONG_PASSWORD, address)


@axes_on
@pytest.mark.django_db
def test_attempts_below_the_limit_still_answer_401() -> None:
    """The Nth failure is refused itself, so only the first N-1 get an informative 401."""
    make_user(username="ana", password=PASSWORD)
    client = APIClient()

    for _ in range(FAILURE_LIMIT - 1):
        response = _login(client, "ana", WRONG_PASSWORD, CHURCH_WIFI)

    assert response.status_code == 401


@axes_on
@pytest.mark.django_db
def test_the_limit_attempt_itself_is_refused() -> None:
    make_user(username="ana", password=PASSWORD)
    client = APIClient()
    for _ in range(FAILURE_LIMIT - 1):
        _login(client, "ana", WRONG_PASSWORD, CHURCH_WIFI)

    response = _login(client, "ana", WRONG_PASSWORD, CHURCH_WIFI)

    assert response.status_code == 429


@axes_on
@pytest.mark.django_db
def test_correct_password_is_refused_once_locked() -> None:
    """The point of the feature: past the limit, even the right password gets nothing."""
    make_user(username="ana", password=PASSWORD)
    client = APIClient()
    _fail_until_locked(client, "ana", CHURCH_WIFI)

    response = _login(client, "ana", PASSWORD, CHURCH_WIFI)

    assert response.status_code == 429
    assert "access" not in json.loads(response.content)


@axes_on
@pytest.mark.django_db
def test_lockout_body_is_the_canonical_envelope() -> None:
    """The Android app parses this shape; the library's default renders HTML instead."""
    make_user(username="ana", password=PASSWORD)
    client = APIClient()
    _fail_until_locked(client, "ana", CHURCH_WIFI)

    body = json.loads(_login(client, "ana", PASSWORD, CHURCH_WIFI).content)

    assert body["error_code"] == ACCOUNT_LOCKED_ERROR_CODE
    assert body["cooloff_seconds"] == 30 * 60


@axes_on
@pytest.mark.django_db
def test_another_member_on_the_same_address_still_logs_in() -> None:
    """The whole congregation shares one NAT address — one mistyper cannot lock it."""
    make_user(username="ana", password=PASSWORD)
    make_user(username="bruno", password=PASSWORD)
    client = APIClient()
    _fail_until_locked(client, "ana", CHURCH_WIFI)

    response = _login(client, "bruno", PASSWORD, CHURCH_WIFI)

    assert response.status_code == 200


@axes_on
@pytest.mark.django_db
def test_locked_user_still_logs_in_from_another_address() -> None:
    """Locking on username alone would be a remote denial of service on the admin."""
    make_user(username="ana", password=PASSWORD)
    client = APIClient()
    _fail_until_locked(client, "ana", OTHER_ADDRESS)

    response = _login(client, "ana", PASSWORD, CHURCH_WIFI)

    assert response.status_code == 200


@axes_on
@pytest.mark.django_db
def test_username_casing_shares_one_budget() -> None:
    """Without AXES_USERNAME_CALLABLE, each casing would get its own five attempts."""
    make_user(username="ana", password=PASSWORD)
    client = APIClient()
    for username in ("ana", "ANA", "Ana", "aNa", "AnA"):
        _login(client, username, WRONG_PASSWORD, CHURCH_WIFI)

    response = _login(client, "ana", PASSWORD, CHURCH_WIFI)

    assert response.status_code == 429


@axes_on
@pytest.mark.django_db
def test_successful_api_login_does_not_reset_the_counter() -> None:
    """Documents plan.md D-8 / tasks.md T-906, so the day it changes a test says so.

    AXES_RESET_ON_SUCCESS is driven by Django's user_logged_in signal, which only
    ``django.contrib.auth.login()`` sends. LoginAPI issues JWTs and creates no session, so
    a correct password leaves the failure count untouched — the count drains through the
    30-minute window instead. The admin login, which does call ``login()``, resets.
    """
    make_user(username="ana", password=PASSWORD)
    client = APIClient()
    for _ in range(FAILURE_LIMIT - 1):
        _login(client, "ana", WRONG_PASSWORD, CHURCH_WIFI)
    assert _login(client, "ana", PASSWORD, CHURCH_WIFI).status_code == 200

    response = _login(client, "ana", WRONG_PASSWORD, CHURCH_WIFI)

    assert response.status_code == 429


@axes_on
@pytest.mark.django_db
def test_django_admin_login_locks_out() -> None:
    """The reason this feature exists: /ipbcb/admin/ is a plain Django view, so none of
    the DRF throttles ever touched it."""
    user = make_user(username="root", password=PASSWORD)
    user.is_staff = user.is_superuser = True
    user.save()
    client = Client()
    for _ in range(FAILURE_LIMIT):
        client.post(
            ADMIN_LOGIN_URL,
            {"username": "root", "password": WRONG_PASSWORD},
            REMOTE_ADDR=CHURCH_WIFI,
        )

    response = client.post(
        ADMIN_LOGIN_URL,
        {"username": "root", "password": PASSWORD},
        REMOTE_ADDR=CHURCH_WIFI,
    )

    assert response.status_code == 429


@pytest.mark.django_db
def test_login_is_unaffected_when_the_lockout_is_disabled() -> None:
    """AXES_ENABLED = False must not turn the missing request into a 500 (plan D-1)."""
    make_user(username="ana", password=PASSWORD)
    client = APIClient()

    for _ in range(FAILURE_LIMIT + 3):
        response = _login(client, "ana", WRONG_PASSWORD, CHURCH_WIFI)

    assert response.status_code == 401
    assert _login(client, "ana", PASSWORD, CHURCH_WIFI).status_code == 200
