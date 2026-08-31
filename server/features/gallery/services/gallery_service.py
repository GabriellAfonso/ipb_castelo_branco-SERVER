from collections.abc import Sequence
from typing import IO

from django.db.models import QuerySet

from core.domain.exceptions import NotFoundError, ValidationError
from core.files.image_validation import detect_image_extension
from features.gallery.dtos.gallery_dtos import UploadResult
from features.gallery.models.gallery import Album, Photo
from features.gallery.repositories.interfaces import GalleryRepository


class GalleryService:
    def __init__(self, repository: GalleryRepository) -> None:
        self._repository = repository

    def list_all_photos(self) -> QuerySet[Photo]:
        return self._repository.list_all_photos()

    def list_photos_by_album(self, album_id: int) -> QuerySet[Photo]:
        return self._repository.list_photos_by_album(album_id)

    def list_all_albums(self) -> QuerySet[Album]:
        return self._repository.list_all_albums()

    def upload_photos(self, album_id: int, files: Sequence[IO[bytes]]) -> UploadResult:
        """Validate and upload photos to an album.

        >>> service.upload_photos(1, [open("photo.jpg", "rb")])
        UploadResult(created_count=1, errors=[])
        """
        album = self._repository.get_album_by_id(album_id)
        if album is None:
            raise NotFoundError(f"Album with id={album_id} not found")

        errors: list[str] = []
        created_count = 0

        for f in files:
            name = getattr(f, "name", "") or ""

            # One bad file must not fail the batch, so the shared validator is caught
            # per file instead of bubbling up.
            try:
                detect_image_extension(f)
            except ValidationError as exc:
                errors.append(f"{name}: {exc}")
                continue

            self._repository.create_photo(album, f, name)
            created_count += 1

        return UploadResult(created_count=created_count, errors=errors)
