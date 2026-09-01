"""Exchange a refresh token for a new pair, rebuilt from the user."""

from typing import Any

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from core.application.dtos.auth_dtos import TokenDTO
from core.domain.exceptions import InvalidRefreshTokenError
from features.accounts.auth.jwt import get_tokens_for_user
from features.accounts.repositories.interfaces import UserRepository


class RefreshService:
    """Issues the new pair from the user record, not from the old token's payload.

    SimpleJWT's own ``TokenRefreshView`` derives the new access token by copying the
    refresh token's claims. A token minted before a claim existed therefore refreshes
    into another token missing that claim — the endpoint answers 200 with credentials it
    will itself reject, and the client never learns to sign in again. Rebuilding from the
    user makes every claim current, for this change and for any claim added later.
    """

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repo = user_repository

    def refresh(self, raw_token: str) -> TokenDTO:
        """Return a fresh pair, or raise ``InvalidRefreshTokenError``.

        >>> service.refresh("eyJhbGciOi...").access
        'eyJhbGciOi...'
        """
        token = self._parse(raw_token)
        user = self._user_repo.get_by_id(token[api_settings.USER_ID_CLAIM])

        # An inactive user must not refresh: JWTAuthentication would reject the token it
        # was just handed, putting the client back in the loop this class exists to close.
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()

        self._revoke(token)
        return get_tokens_for_user(user)

    def _parse(self, raw_token: str) -> RefreshToken:
        """Validate signature, expiry and blacklist before anything is trusted."""
        try:
            # The stub types the argument as Token, but the documented runtime contract is
            # the encoded string — what SimpleJWT's own TokenRefreshSerializer passes.
            return RefreshToken(raw_token)  # type: ignore[arg-type]
        except (TokenError, KeyError, TypeError) as exc:
            raise InvalidRefreshTokenError() from exc

    def _revoke(self, token: Any) -> None:
        """Blacklist the presented token, so rotation still means single use."""
        if not api_settings.ROTATE_REFRESH_TOKENS or not api_settings.BLACKLIST_AFTER_ROTATION:
            return
        try:
            token.blacklist()
        except AttributeError:
            # token_blacklist is not installed; rotation is then best-effort.
            pass
