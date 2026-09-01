from typing import cast

from dependency_injector.wiring import inject, Provide
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from features.accounts.models.user import User
from features.accounts.serializers.serializers import ProfileSerializer
from features.accounts.services.profile_service import ProfileService
from config.di import Container
from core.http.utils import _not_modified_or_response


class ProfilePhotoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @inject
    def post(
        self,
        request: Request,
        profile_service: ProfileService = Provide[Container.profile_service],
    ) -> Response:
        user = cast(User, request.user)
        photo = request.FILES.get("photo")
        if not photo:
            return Response({"detail": "Nenhuma foto enviada."}, status=status.HTTP_400_BAD_REQUEST)

        # The file object is handed over whole: the service validates it and the
        # repository streams it, so the upload is never materialised in memory here.
        profile = profile_service.upload_photo(user, photo)

        return Response(
            {
                "detail": "Foto de perfil atualizada com sucesso.",
                "photo_url": request.build_absolute_uri(profile.photo.url)
                if profile.photo
                else None,
            },
            status=status.HTTP_200_OK,
        )

    @inject
    def delete(
        self,
        request: Request,
        profile_service: ProfileService = Provide[Container.profile_service],
    ) -> Response:
        user = cast(User, request.user)
        profile_service.delete_photo(user)
        return Response({"detail": "Foto de perfil removida."}, status=status.HTTP_204_NO_CONTENT)


class MeProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @inject
    def get(
        self,
        request: Request,
        profile_service: ProfileService = Provide[Container.profile_service],
    ) -> Response:
        user = cast(User, request.user)
        profile = profile_service.get_profile(user)
        serializer = ProfileSerializer(profile, context={"request": request})
        data = serializer.data
        return _not_modified_or_response(request, data, private=True)

    @inject
    def patch(
        self,
        request: Request,
        profile_service: ProfileService = Provide[Container.profile_service],
    ) -> Response:
        user = cast(User, request.user)
        profile = profile_service.get_profile(user)
        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
