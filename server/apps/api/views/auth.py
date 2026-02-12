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

# injeção
from dependency_injector.wiring import inject, Provide
from config.dependencies import Container
from core.domain.interfaces.repositories.user_repository import UserRepository


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


class RefreshTokenAPI(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        refresh_str = request.data.get("refresh")
        if not refresh_str:
            return Response(
                {"refresh": [_("Este campo é obrigatório.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_str)

            user_id = refresh.get("user_id")
            user = User.objects.filter(id=user_id).first() if user_id else None

            access = refresh.access_token
            if user is not None:
                add_custom_claims(access, user)  # type: ignore[arg-type]

            data: dict[str, str] = {
                "access": str(access),
                "token": str(access),  # compat
            }

            if api_settings.ROTATE_REFRESH_TOKENS:
                refresh.set_jti()
                refresh.set_exp()
                refresh.set_iat()

                if api_settings.BLACKLIST_AFTER_ROTATION:
                    try:
                        refresh.blacklist()
                    except AttributeError:
                        pass

                if user is not None:
                    add_custom_claims(refresh, user)

                data["refresh"] = str(refresh)

            print("chamou refresh")
            return Response(data, status=status.HTTP_200_OK)

        except Exception:
            return Response(
                {"detail": [_("Token inválido ou expirado")]},
                status=status.HTTP_401_UNAUTHORIZED,
            )
