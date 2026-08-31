import io

import pytest
from django.test import Client
from PIL import Image

from features.gallery.models.gallery import Album, Photo
from core.files.image_validation import MAX_IMAGE_BYTES


UPLOAD_URL = "/admin/gallery/album/upload/"


def _make_image_file(
    name: str = "test.jpg",
    fmt: str = "JPEG",
    size: tuple[int, int] = (10, 10),
) -> io.BytesIO:
    buf = io.BytesIO()
    Image.new("RGB", size).save(buf, format=fmt)
    buf.seek(0)
    buf.name = name
    return buf


@pytest.mark.django_db
class TestUploadPhotosView:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.client = Client()
        self.client.login(username="admin", password="admin")
        self.album = Album.objects.create(name="Upload Test")

    def _login_admin(self) -> None:
        from features.accounts.models.user import User

        user = User.objects.create_superuser(username="admin_upload", password="adminpass123")
        self.client.force_login(user)

    def test_get_returns_html_form(self) -> None:
        self._login_admin()
        response = self.client.get(UPLOAD_URL)
        assert response.status_code == 200
        assert b"<form" in response.content

    def test_post_valid_upload_creates_photo(self) -> None:
        self._login_admin()
        img = _make_image_file()

        response = self.client.post(
            UPLOAD_URL,
            {"album": self.album.pk, "images": img},
        )

        assert response.status_code == 302
        assert Photo.objects.filter(album=self.album).count() == 1

    def test_post_without_album_returns_error(self) -> None:
        self._login_admin()
        img = _make_image_file()

        response = self.client.post(UPLOAD_URL, {"images": img})

        assert response.status_code == 200
        assert b"Selecione" in response.content

    def test_post_without_files_returns_error(self) -> None:
        self._login_admin()

        response = self.client.post(UPLOAD_URL, {"album": self.album.pk})

        assert response.status_code == 200
        assert b"Selecione" in response.content

    def test_post_oversized_file_returns_error(self) -> None:
        from unittest.mock import PropertyMock, patch

        self._login_admin()
        img = _make_image_file()
        from django.core.files.uploadedfile import InMemoryUploadedFile

        oversized = InMemoryUploadedFile(
            file=img,
            field_name="images",
            name="big.jpg",
            content_type="image/jpeg",
            size=MAX_IMAGE_BYTES + 1,
            charset=None,
        )

        with patch.object(
            type(oversized), "size", new_callable=PropertyMock, return_value=MAX_IMAGE_BYTES + 1
        ):
            response = self.client.post(
                UPLOAD_URL,
                {"album": self.album.pk, "images": oversized},
            )

        assert response.status_code == 200
        assert b"muito grande" in response.content
        assert Photo.objects.count() == 0

    def test_post_invalid_image_returns_error(self) -> None:
        self._login_admin()
        buf = io.BytesIO(b"not-an-image")
        buf.name = "bad.jpg"

        response = self.client.post(
            UPLOAD_URL,
            {"album": self.album.pk, "images": buf},
        )

        assert response.status_code == 200
        assert b"formato" in response.content.lower()
        assert Photo.objects.count() == 0
