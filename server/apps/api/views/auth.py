from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from dependency_injector.wiring import inject, Provide
from pydantic import ValidationError  # noqa
from apps.api.auth.jwt import get_tokens_for_user
from apps.persistence.models.profile import User
from core.application.dtos.auth_dtos import LoginDTO
from apps.api.serializers.register_serializer import RegisterSerializer
from config.dependencies import Container
from core.domain.interfaces.repositories.user_repository import UserRepository
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from apps.persistence.models.profile import User

class RegisterAPI(APIView):

    @inject
    def post(self, request: Request,
             user_repo: UserRepository = Provide[Container.user_repository]) -> Response:

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = serializer.create_dto()
        user: User = user_repo.create(dto)

        token_dto = get_tokens_for_user(user)

        return Response(token_dto.model_dump(), status=status.HTTP_201_CREATED)


class LoginAPI(APIView):
    @staticmethod
    def post(request: Request) -> Response:
        invalid_credentials_error = Response(
            {"detail": _("Nome de usuário ou senha inválidos.")},
            status=status.HTTP_401_UNAUTHORIZED,
        )

        try:
            login_dto = LoginDTO(**request.data)
        except ValidationError:
            return invalid_credentials_error

        user = authenticate(
            username=login_dto.username,
            password=login_dto.password
        )

        if user is None:
            return invalid_credentials_error

        token_dto = get_tokens_for_user(user)
        return Response(token_dto.model_dump(), status=status.HTTP_200_OK)



class GoogleLoginAPI(APIView):
    @staticmethod
    def post(request: Request) -> Response:
        token = request.data.get("id_token")
        if not token:
            return Response({"detail": "id_token é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return Response({"detail": "Token do Google inválido."}, status=status.HTTP_401_UNAUTHORIZED)

        google_id = idinfo["sub"]
        email = idinfo.get("email", "")
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")

        # Pega ou cria o usuário pelo google_id ou email
        user = User.objects.filter(email=email).first()
        if not user:
            username = email.split("@")[0]
            # Garante username único
            base = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_unusable_password()
            user.save()

        token_dto = get_tokens_for_user(user)
        return Response(token_dto.model_dump(), status=status.HTTP_200_OK)