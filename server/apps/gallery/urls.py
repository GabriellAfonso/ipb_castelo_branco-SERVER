from django.urls import path

from apps.gallery.views.gallery import AlbumPhotoListAPIView, PhotoListAPIView
from apps.gallery.views.upload import upload_photos

urlpatterns = [
    path("gallery/upload/", upload_photos, name="upload_photos"),
    path("api/photos/", PhotoListAPIView.as_view()),
    path("api/albums/<int:album_id>/photos/", AlbumPhotoListAPIView.as_view()),
]
