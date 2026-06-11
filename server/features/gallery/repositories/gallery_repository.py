from django.db.models import QuerySet

from features.gallery.models.gallery import Album, Photo


class DjangoGalleryRepository:
    """Gallery repository using Django ORM."""

    def list_all_photos(self) -> QuerySet[Photo]:
        return Photo.objects.select_related("album").order_by("album__name", "uploaded_at")

    def list_photos_by_album(self, album_id: int) -> QuerySet[Photo]:
        return (
            Photo.objects.filter(album_id=album_id).select_related("album").order_by("uploaded_at")
        )

    def list_all_albums(self) -> QuerySet[Album]:
        return Album.objects.all()

    def get_album_by_id(self, album_id: int) -> Album | None:
        return Album.objects.filter(pk=album_id).first()

    def create_photo(self, album: Album, image: object, name: str) -> Photo:
        return Photo.objects.create(album=album, image=image, name=name)
