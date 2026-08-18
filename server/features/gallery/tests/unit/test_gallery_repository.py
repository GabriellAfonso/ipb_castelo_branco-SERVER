import pytest

from features.gallery.models.gallery import Album, Photo
from features.gallery.repositories.gallery_repository import GalleryRepositoryImpl


@pytest.mark.django_db
class TestListAllPhotos:
    def test_returns_photos_ordered_by_album_and_upload(self) -> None:
        repo = GalleryRepositoryImpl()
        album_b = Album.objects.create(name="B")
        album_a = Album.objects.create(name="A")
        Photo.objects.create(album=album_b, name="b1.jpg", image="b1.jpg")
        Photo.objects.create(album=album_a, name="a1.jpg", image="a1.jpg")

        photos = list(repo.list_all_photos())

        assert photos[0].album.name == "A"
        assert photos[1].album.name == "B"

    def test_returns_empty_when_no_photos(self) -> None:
        repo = GalleryRepositoryImpl()
        assert list(repo.list_all_photos()) == []


@pytest.mark.django_db
class TestListPhotosByAlbum:
    def test_filters_by_album_id(self) -> None:
        repo = GalleryRepositoryImpl()
        album1 = Album.objects.create(name="One")
        album2 = Album.objects.create(name="Two")
        Photo.objects.create(album=album1, name="p1.jpg", image="p1.jpg")
        Photo.objects.create(album=album2, name="p2.jpg", image="p2.jpg")

        photos = list(repo.list_photos_by_album(album1.pk))

        assert len(photos) == 1
        assert photos[0].album == album1

    def test_returns_empty_for_nonexistent_album(self) -> None:
        repo = GalleryRepositoryImpl()
        assert list(repo.list_photos_by_album(9999)) == []


@pytest.mark.django_db
class TestListAllAlbums:
    def test_returns_all_albums(self) -> None:
        repo = GalleryRepositoryImpl()
        Album.objects.create(name="X")
        Album.objects.create(name="Y")

        assert repo.list_all_albums().count() == 2


@pytest.mark.django_db
class TestGetAlbumById:
    def test_returns_album_when_exists(self) -> None:
        repo = GalleryRepositoryImpl()
        album = Album.objects.create(name="Found")

        assert repo.get_album_by_id(album.pk) == album

    def test_returns_none_when_not_found(self) -> None:
        repo = GalleryRepositoryImpl()
        assert repo.get_album_by_id(9999) is None


@pytest.mark.django_db
class TestCreatePhoto:
    def test_creates_and_returns_photo(self) -> None:
        repo = GalleryRepositoryImpl()
        album = Album.objects.create(name="Create")

        photo = repo.create_photo(album, "fake.jpg", "foto.jpg")

        assert photo.pk is not None
        assert photo.album == album
        assert photo.name == "foto.jpg"
