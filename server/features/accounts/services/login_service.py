from django.contrib.auth import authenticate

from core.application.dtos.auth_dtos import LoginDTO, TokenDTO
from core.domain.exceptions import InvalidCredentialsError
from core.metrics import LOGIN_COUNTER
from features.accounts.auth.jwt import get_tokens_for_user


class LoginService:
    def login(self, dto: LoginDTO) -> TokenDTO:
        user = authenticate(username=dto.username, password=dto.password)
        if user is None:
            LOGIN_COUNTER.labels(result="failure", login_type="credentials").inc()
            raise InvalidCredentialsError()

        LOGIN_COUNTER.labels(result="success", login_type="credentials").inc()
        return get_tokens_for_user(user)
