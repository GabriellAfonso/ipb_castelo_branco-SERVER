from typing import Protocol

from django.db.models import QuerySet

from features.gallery.models.gallery import Album, Photo


class GalleryRepository(Protocol):
    """Contract for gallery persistence operations."""

    def list_all_photos(self) -> QuerySet[Photo]: ...

    def list_photos_by_album(self, album_id: int) -> QuerySet[Photo]: ...

    def list_all_albums(self) -> QuerySet[Album]: ...

    def get_album_by_id(self, album_id: int) -> Album | None: ...

    def create_photo(self, album: Album, image: object, name: str) -> Photo: ...
