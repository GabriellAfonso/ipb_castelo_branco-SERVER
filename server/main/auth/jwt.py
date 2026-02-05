from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


def _safe_get_profile_claims(user: User) -> dict[str, Any]:
    profile = getattr(user, "profile", None)
    if not profile:
        return {}

    return {
        "profile_active": bool(getattr(profile, "active", True)),
        "profile_is_member": bool(getattr(profile, "is_member", False)),
        "profile_name": getattr(profile, "name", "") or "",
    }


def add_custom_claims(token: RefreshToken, user: User) -> None:
    """Attach custom claims onto a JWT token payload.

    Keep claims small and non-sensitive; JWTs are readable by the client.
    """

    token["username"] = user.username
    token["email"] = user.email or ""
    token["first_name"] = user.first_name or ""
    token["last_name"] = user.last_name or ""

    token["is_staff"] = bool(user.is_staff)
    token["is_superuser"] = bool(user.is_superuser)
    token["is_active"] = bool(user.is_active)

    for key, value in _safe_get_profile_claims(user).items():
        token[key] = value


def get_tokens_for_user(user: User) -> dict[str, str]:
    """Return refresh/access tokens with custom claims."""

    refresh = RefreshToken.for_user(user)
    add_custom_claims(refresh, user)

    access = refresh.access_token
    # Be explicit: ensure access also contains the custom claims.
    add_custom_claims(access, user)  # type: ignore[arg-type]

    return {
        "refresh": str(refresh),
        "access": str(access),
    }
