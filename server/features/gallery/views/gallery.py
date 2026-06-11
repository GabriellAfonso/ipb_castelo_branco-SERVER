from dependency_injector.wiring import Provide, inject
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.di import Container
from core.http.permissions import IsMemberUser
from features.gallery.serializers.serializers import PhotoListSerializer
from features.gallery.services.gallery_service import GalleryService


class PhotoListAPIView(APIView):
    serializer_class = PhotoListSerializer
    permission_classes = [IsMemberUser]

    @inject
    def get(
        self,
        request: Request,
        gallery_service: GalleryService = Provide[Container.gallery_service],
    ) -> Response:
        photos = gallery_service.list_all_photos()
        serializer = PhotoListSerializer(photos, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AlbumPhotoListAPIView(APIView):
    serializer_class = PhotoListSerializer
    permission_classes = [IsMemberUser]

    @inject
    def get(
        self,
        request: Request,
        album_id: int,
        gallery_service: GalleryService = Provide[Container.gallery_service],
    ) -> Response:
        photos = gallery_service.list_photos_by_album(album_id)
        serializer = PhotoListSerializer(photos, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
