from rest_framework.test import APIClient

HEALTH_URL = "/health/"


def test_health_check_returns_200() -> None:
    client = APIClient()
    response = client.get(HEALTH_URL)
    assert response.status_code == 200


def test_health_check_returns_status_ok() -> None:
    client = APIClient()
    response = client.get(HEALTH_URL)
    assert response.json() == {"status": "ok"}


def test_health_check_content_type_is_json() -> None:
    client = APIClient()
    response = client.get(HEALTH_URL)
    assert "application/json" in response["Content-Type"]


def test_health_check_accessible_without_authentication() -> None:
    client = APIClient()
    response = client.get(HEALTH_URL)
    assert response.status_code not in (401, 403)
