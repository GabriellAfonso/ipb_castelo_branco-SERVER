import io
from unittest.mock import MagicMock

import pytest
from PIL import Image

from core.domain.exceptions import NotFoundError
from features.gallery.services.gallery_service import GalleryService, MAX_FILE_SIZE


def _make_image_bytes(name: str = "test.jpg", fmt: str = "JPEG") -> io.BytesIO:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format=fmt)
    buf.seek(0)
    setattr(buf, "name", name)
    setattr(buf, "size", buf.getbuffer().nbytes)
    return buf


def _make_repo() -> MagicMock:
    return MagicMock()


class TestListAllPhotos:
    def test_delegates_to_repository(self) -> None:
        repo = _make_repo()
        service = GalleryService(repository=repo)

        service.list_all_photos()

        repo.list_all_photos.assert_called_once()


class TestListPhotosByAlbum:
    def test_delegates_to_repository(self) -> None:
        repo = _make_repo()
        service = GalleryService(repository=repo)

        service.list_photos_by_album(42)

        repo.list_photos_by_album.assert_called_once_with(42)


class TestListAllAlbums:
    def test_delegates_to_repository(self) -> None:
        repo = _make_repo()
        service = GalleryService(repository=repo)

        service.list_all_albums()

        repo.list_all_albums.assert_called_once()


class TestUploadPhotos:
    def test_raises_not_found_when_album_missing(self) -> None:
        repo = _make_repo()
        repo.get_album_by_id.return_value = None
        service = GalleryService(repository=repo)

        with pytest.raises(NotFoundError, match="id=999"):
            service.upload_photos(999, [_make_image_bytes()])

    def test_creates_photo_for_valid_file(self) -> None:
        repo = _make_repo()
        album = MagicMock()
        repo.get_album_by_id.return_value = album
        service = GalleryService(repository=repo)

        result = service.upload_photos(1, [_make_image_bytes("photo.jpg")])

        assert result.created_count == 1
        assert result.errors == []
        repo.create_photo.assert_called_once_with(album, _any(), "photo.jpg")

    def test_rejects_oversized_file(self) -> None:
        repo = _make_repo()
        repo.get_album_by_id.return_value = MagicMock()
        service = GalleryService(repository=repo)

        big_file = _make_image_bytes("big.jpg")
        setattr(big_file, "size", MAX_FILE_SIZE + 1)

        result = service.upload_photos(1, [big_file])

        assert result.created_count == 0
        assert len(result.errors) == 1
        assert "muito grande" in result.errors[0]
        repo.create_photo.assert_not_called()

    def test_rejects_invalid_image(self) -> None:
        repo = _make_repo()
        repo.get_album_by_id.return_value = MagicMock()
        service = GalleryService(repository=repo)

        bad_file = io.BytesIO(b"not-an-image")
        setattr(bad_file, "name", "bad.jpg")
        setattr(bad_file, "size", 100)

        result = service.upload_photos(1, [bad_file])

        assert result.created_count == 0
        assert "formato" in result.errors[0].lower()
        repo.create_photo.assert_not_called()

    def test_mixed_valid_and_invalid_files(self) -> None:
        repo = _make_repo()
        album = MagicMock()
        repo.get_album_by_id.return_value = album
        service = GalleryService(repository=repo)

        good = _make_image_bytes("ok.jpg")
        bad = io.BytesIO(b"nope")
        setattr(bad, "name", "bad.jpg")
        setattr(bad, "size", 50)

        result = service.upload_photos(1, [good, bad])

        assert result.created_count == 1
        assert len(result.errors) == 1
        repo.create_photo.assert_called_once()

    def test_file_without_size_skips_size_check(self) -> None:
        repo = _make_repo()
        repo.get_album_by_id.return_value = MagicMock()
        service = GalleryService(repository=repo)

        img = _make_image_bytes("nosiz.jpg")
        delattr(img, "size")  # no size attribute

        result = service.upload_photos(1, [img])

        assert result.created_count == 1
        assert result.errors == []


def _any() -> object:
    """Helper that matches anything in assert_called_with."""
    from unittest.mock import ANY

    return ANY
