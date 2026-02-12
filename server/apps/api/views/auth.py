from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.api.auth.jwt import add_custom_claims, get_tokens_for_user
from apps.persistence.models.profile import User

from apps.api.serializers import RegisterSerializer


class RegisterAPI(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = serializer.save()

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "refresh": tokens["refresh"],
                "token": tokens["access"],  # compat
                "access": tokens["access"],
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPI(APIView):
    def post(self, request: Request) -> Response:
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user is not None:
            tokens = get_tokens_for_user(user)
            return Response(
                {
                    "refresh": tokens["refresh"],
                    "token": tokens["access"],  # compat
                    "access": tokens["access"],
                }
            )

        return Response(
            {"detail": [_("Credenciais inválidas")]},
            status=status.HTTP_401_UNAUTHORIZED,
        )


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
