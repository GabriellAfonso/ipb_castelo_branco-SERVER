from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.api.permissions import IsMemberUser
from apps.persistence.models.gallery import Photo
from apps.api.serializers.gallery_serializers import PhotoListSerializer


class PhotoListAPIView(APIView):
    permission_classes = [IsAuthenticated,IsMemberUser]

    @staticmethod
    def get(request):
        photos = (
            Photo.objects
            .select_related("album")
            .order_by("album__name", "uploaded_at")
        )

        serializer = PhotoListSerializer(
            photos,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


#Opcional: endpoint para listar fotos de um álbum específico
class AlbumPhotoListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, album_id):
        photos = (
            Photo.objects
            .filter(album_id=album_id)
            .select_related("album")
            .order_by("uploaded_at")
        )

        serializer = PhotoListSerializer(
            photos,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data, status=status.HTTP_200_OK)