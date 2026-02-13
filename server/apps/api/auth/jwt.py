from apps.persistence.models.profile import User
from rest_framework_simplejwt.tokens import RefreshToken
from core.application.dtos.auth_dtos import TokenDTO


def get_tokens_for_user(user: User) -> TokenDTO:
    refresh = RefreshToken.for_user(user)

    return TokenDTO(
        access=str(refresh.access_token),
        refresh=str(refresh),
    )
