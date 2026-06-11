from django.contrib.auth import authenticate

from core.application.dtos.auth_dtos import LoginDTO, TokenDTO
from core.domain.exceptions import InvalidCredentialsError
from features.accounts.auth.jwt import get_tokens_for_user


class LoginService:
    def login(self, dto: LoginDTO) -> TokenDTO:
        user = authenticate(username=dto.username, password=dto.password)
        if user is None:
            raise InvalidCredentialsError()

        return get_tokens_for_user(user)
