"""Regression: these payloads used to reach the handler as unhandled TypeError/ValueError
and come back as 500, telling the client to retry a request that can never succeed."""

import pytest
from rest_framework.test import APIClient

from conftest import make_admin_client

LOGIN_URL = "/api/auth/login/"


@pytest.mark.django_db
@pytest.mark.parametrize("body", [["a"], "abc", 42])
def test_login_rejects_a_body_that_is_not_an_object(body: object) -> None:
    response = APIClient().post(LOGIN_URL, body, format="json")

    assert response.status_code == 400
    assert response.data["error_code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_login_still_answers_400_for_wrong_fields() -> None:
    """The pydantic path already worked; this pins it against the new guard."""
    response = APIClient().post(LOGIN_URL, {"foo": "bar"}, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("song_id", ["abc", [1], {}, ""])
def test_chord_chart_rejects_a_non_integer_song_id(song_id: object) -> None:
    client, _ = make_admin_client()

    response = client.post("/api/chord-charts/", {"song_id": song_id}, format="json")

    assert response.status_code == 400
    assert response.data["error_code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_lyrics_rejects_a_non_integer_song_id() -> None:
    client, _ = make_admin_client()

    response = client.post("/api/lyrics/", {"song_id": "abc"}, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
def test_service_window_patch_rejects_a_body_that_is_not_an_object() -> None:
    client, _ = make_admin_client()

    response = client.patch("/api/hymnal-history/service-windows/1/", ["x"], format="json")

    assert response.status_code in (400, 404)
    if response.status_code == 400:
        assert response.data["error_code"] == "VALIDATION_ERROR"
