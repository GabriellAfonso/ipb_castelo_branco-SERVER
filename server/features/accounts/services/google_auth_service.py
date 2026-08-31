import logging
from io import BytesIO

import requests as http_requests
from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from core.application.dtos.auth_dtos import TokenDTO
from core.application.dtos.google_auth_dto import GoogleUserDTO
from core.files.image_validation import detect_image_extension
from core.domain.exceptions import (
    GoogleUserCreationError,
    InvalidGoogleTokenError,
    UnverifiedGoogleEmailError,
    ValidationError,
)
from core.metrics import LOGIN_COUNTER
from features.accounts.auth.jwt import get_tokens_for_user
from features.accounts.models.user import User
from features.accounts.repositories.interfaces import ProfileRepository, UserRepository
from features.accounts.validators import sanitize_username

logger = logging.getLogger(__name__)


class GoogleAuthService:
    def __init__(
        self, user_repository: UserRepository, profile_repository: ProfileRepository
    ) -> None:
        self._user_repo = user_repository
        self._profile_repo = profile_repository

    def authenticate_google(self, token: str) -> TokenDTO:
        try:
            google_user = self._verify_token(token)
            user = self._get_or_create_user(google_user)
        except Exception:
            LOGIN_COUNTER.labels(result="failure", login_type="google").inc()
            raise
        self._sync_profile_photo(user, google_user.picture_url)
        LOGIN_COUNTER.labels(result="success", login_type="google").inc()
        return get_tokens_for_user(user)

    def _verify_token(self, token: str) -> GoogleUserDTO:
        try:
            idinfo = id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            raise InvalidGoogleTokenError()

        dto = GoogleUserDTO(
            email=idinfo.get("email", ""),
            first_name=idinfo.get("given_name", ""),
            last_name=idinfo.get("family_name", ""),
            picture_url=idinfo.get("picture"),
            email_verified=idinfo.get("email_verified", False),
        )

        if not dto.email_verified or not dto.email:
            raise UnverifiedGoogleEmailError()

        return dto

    def _get_or_create_user(self, dto: GoogleUserDTO) -> User:
        user = self._user_repo.get_by_email(dto.email)
        if user:
            return user

        # The e-mail local part never passes through RegisterSerializer, so it is the
        # one way a username breaking the rules could still be created.
        base_username = sanitize_username(dto.email.split("@")[0])
        username = self._user_repo.generate_unique_username(base_username)

        try:
            return self._user_repo.create_google_user(
                email=dto.email,
                username=username,
                first_name=dto.first_name,
                last_name=dto.last_name,
            )
        except Exception:
            raise GoogleUserCreationError(dto.email)

    def _sync_profile_photo(self, user: User, picture_url: str | None) -> None:
        if not picture_url:
            return

        profile, _ = self._profile_repo.get_or_create(user)
        if profile.photo:
            return

        photo_url = picture_url.split("=s")[0] + "=s400-c"
        try:
            response = http_requests.get(photo_url, timeout=5)
            if response.status_code == 200:
                # Remote bytes are still untrusted bytes, and the extension came from a
                # URL. Same content check as a user upload.
                upload = BytesIO(response.content)
                extension = detect_image_extension(upload)
                self._profile_repo.save_photo(profile, extension, upload)
        except (
            OSError,
            ValueError,
            ValidationError,
            http_requests.RequestException,
        ) as exc:
            # A bad avatar must never block a valid login.
            logger.warning("Failed to save Google profile photo: %s", exc)
