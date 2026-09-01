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
    RefreshSerializer,
    RegisterSerializer,
    TokenSerializer,
)
from config.di import Container
from core.application.dtos.auth_dtos import LoginDTO
from core.domain.exceptions import ValidationError
from core.http.parsing import require_object_body
from features.accounts.services.google_auth_service import GoogleAuthService
from features.accounts.services.login_service import LoginService
from features.accounts.services.refresh_service import RefreshService
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
        login_dto = LoginDTO(**require_object_body(request.data))
        # The underlying HttpRequest, not DRF's wrapper: the axes backend flags the object it
        # is given, and AxesMiddleware only ever sees the Django one. Flagging the wrapper
        # would leave the lockout recorded but never enforced.
        token_dto = login_service.login(login_dto, request._request)
        return Response(token_dto.model_dump(), status=status.HTTP_200_OK)


class RefreshAPI(APIView):
    """POST: exchange a refresh token for a new pair.

    Replaces SimpleJWT's ``TokenRefreshView``: that one copies the presented token's
    claims into the new access token, so a token minted before a claim existed refreshes
    into another one missing it — 200 with credentials the API itself rejects.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=RefreshSerializer, responses={200: TokenSerializer, 401: None})
    @inject
    def post(
        self,
        request: Request,
        refresh_service: RefreshService = Provide[Container.refresh_service],
    ) -> Response:
        body = require_object_body(request.data)
        raw_token = body.get("refresh")
        if not raw_token:
            raise ValidationError("Field 'refresh' is required.")

        # InvalidRefreshTokenError bubbles up to custom_exception_handler as a 401.
        token_dto = refresh_service.refresh(str(raw_token))
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
