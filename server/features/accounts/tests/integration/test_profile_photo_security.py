"""End-to-end guards for the profile photo upload.

Regression suite for the finding that ``Profile.photo.save()`` bypasses the field
validators, so the endpoint accepted arbitrary bytes under an arbitrary extension.
"""

import tempfile
from io import BytesIO

import pytest
from django.test import override_settings
from PIL import Image

from conftest import make_auth_client, make_user

PHOTO_URL = "/api/me/profile/photo/"


def _image_named(name: str, fmt: str = "PNG") -> BytesIO:
    buffer = BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format=fmt)
    buffer.seek(0)
    buffer.name = name
    return buffer


@pytest.mark.django_db
def test_stores_a_png_named_evil_html_as_png() -> None:
    """The extension follows the decoded format, so no HTML lands in MEDIA_ROOT."""
    with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
        user = make_user(username="evilname", password="testpass123")

        response = make_auth_client(user).post(
            PHOTO_URL, {"photo": _image_named("evil.html")}, format="multipart"
        )

        assert response.status_code == 200
        user.profile.refresh_from_db()
        stored = user.profile.photo.name or ""
        assert stored.endswith(".png")
        assert ".html" not in stored


@pytest.mark.django_db
def test_rejects_html_disguised_as_an_image() -> None:
    with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
        user = make_user(username="htmluser", password="testpass123")
        payload = BytesIO(b"<html><script>alert(document.cookie)</script></html>")
        payload.name = "avatar.png"

        response = make_auth_client(user).post(PHOTO_URL, {"photo": payload}, format="multipart")

        assert response.status_code == 400
        assert response.data["error_code"] == "VALIDATION_ERROR"
        user.profile.refresh_from_db()
        assert not user.profile.photo


@pytest.mark.django_db
def test_rejects_svg_even_though_it_is_an_image_format() -> None:
    with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
        user = make_user(username="svguser", password="testpass123")
        payload = BytesIO(b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>')
        payload.name = "avatar.svg"

        response = make_auth_client(user).post(PHOTO_URL, {"photo": payload}, format="multipart")

        assert response.status_code == 400


@pytest.mark.django_db
def test_a_rejected_upload_keeps_the_existing_photo() -> None:
    with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
        user = make_user(username="keepuser", password="testpass123")
        client = make_auth_client(user)
        client.post(PHOTO_URL, {"photo": _image_named("first.png")}, format="multipart")
        user.profile.refresh_from_db()
        original = user.profile.photo.name

        bad = BytesIO(b"not an image")
        bad.name = "second.png"
        response = client.post(PHOTO_URL, {"photo": bad}, format="multipart")

        assert response.status_code == 400
        user.profile.refresh_from_db()
        assert user.profile.photo.name == original


@pytest.mark.django_db
def test_upload_requires_authentication() -> None:
    from rest_framework.test import APIClient

    response = APIClient().post(PHOTO_URL, {"photo": _image_named("a.png")}, format="multipart")

    assert response.status_code == 401
