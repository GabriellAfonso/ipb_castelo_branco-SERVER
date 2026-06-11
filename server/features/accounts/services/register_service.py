from core.application.dtos.auth_dtos import RegisterDTO, TokenDTO
from core.domain.exceptions import UsernameAlreadyExistsError
from features.accounts.auth.jwt import get_tokens_for_user
from features.accounts.repositories.interfaces import UserRepository


class RegisterService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repo = user_repository

    def register(self, dto: RegisterDTO) -> TokenDTO:
        if self._user_repo.username_exists(dto.username):
            raise UsernameAlreadyExistsError(dto.username)

        user = self._user_repo.create(dto)
        return get_tokens_for_user(user)
