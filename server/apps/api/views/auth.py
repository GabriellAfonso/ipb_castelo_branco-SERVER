from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from pydantic import ValidationError

from apps.api.auth.jwt import add_custom_claims, get_tokens_for_user
from apps.persistence.models.profile import User
from core.application.dtos.auth_dtos import LoginDTO, TokenDTO

from apps.api.serializers.register_serializer import RegisterSerializer
from rest_framework_simplejwt.views import TokenRefreshView
# injeção
from dependency_injector.wiring import inject, Provide
from config.dependencies import Container
from core.domain.interfaces.repositories.user_repository import UserRepository
from apps.api.serializers.token_refresh_serializer import CustomTokenRefreshSerializer
from rest_framework_simplejwt.exceptions import TokenError


class RegisterAPI(APIView):
    authentication_classes = []
    permission_classes = []

    @inject
    def post(self, request: Request,
             user_repo: UserRepository = Provide[Container.user_repository]) -> Response:

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = serializer.create_dto()
        user: User = user_repo.create(dto)

        tokens = get_tokens_for_user(user)
        return Response({
            "refresh": tokens["refresh"],
            "token": tokens["access"],
            "access": tokens["access"],
        }, status=status.HTTP_201_CREATED)


class LoginAPI(APIView):
    def post(self, request):
        try:
            login_dto = LoginDTO(**request.data)
        except ValidationError as e:
            return Response(
                {"detail": e.errors()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=login_dto.username,
                            password=login_dto.password)

        if user is None:
            return Response(
                {"detail": _("Nome de usuário ou senha inválidos.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)
        token_dto = TokenDTO(
            access=tokens["access"], refresh=tokens.get("refresh"))

        return Response(token_dto.model_dump(), status=status.HTTP_200_OK)
