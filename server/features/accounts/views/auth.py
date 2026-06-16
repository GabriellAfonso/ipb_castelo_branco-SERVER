from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from dependency_injector.wiring import inject, Provide

from features.accounts.serializers.serializers import (
    GoogleLoginSerializer,
    LoginSerializer,
    RegisterSerializer,
    TokenSerializer,
)
from config.di import Container
from core.application.dtos.auth_dtos import LoginDTO
from features.accounts.services.google_auth_service import GoogleAuthService
from features.accounts.services.login_service import LoginService
from features.accounts.services.register_service import RegisterService


class RegisterAPI(APIView):
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @inject
    def post(
        self,
        request: Request,
        register_service: RegisterService = Provide[Container.register_service],
    ) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = serializer.create_dto()
        token_dto = register_service.register(dto)

        return Response(token_dto.model_dump(), status=status.HTTP_201_CREATED)


class LoginAPI(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: TokenSerializer, 401: None})
    @inject
    def post(
        self,
        request: Request,
        login_service: LoginService = Provide[Container.login_service],
    ) -> Response:
        # Pydantic ValidationError and InvalidCredentialsError bubble up
        # to custom_exception_handler
        login_dto = LoginDTO(**request.data)
        token_dto = login_service.login(login_dto)
        return Response(token_dto.model_dump(), status=status.HTTP_200_OK)


class GoogleLoginAPI(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        request=GoogleLoginSerializer, responses={200: TokenSerializer, 400: None, 401: None}
    )
    @inject
    def post(
        self,
        request: Request,
        google_auth_service: GoogleAuthService = Provide[Container.google_auth_service],
    ) -> Response:
        token = request.data.get("id_token")
        if not token:
            return Response(
                {"detail": "id_token é obrigatório."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Domain exceptions (InvalidGoogleTokenError, UnverifiedGoogleEmailError,
        # GoogleUserCreationError) bubble up to custom_exception_handler
        token_dto = google_auth_service.authenticate_google(token)
        return Response(token_dto.model_dump(), status=status.HTTP_200_OK)
