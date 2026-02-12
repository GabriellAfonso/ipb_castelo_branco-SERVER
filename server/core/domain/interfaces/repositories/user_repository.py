from typing import Optional, Protocol

from apps.persistence.models.profile import User
from core.application.dtos.auth_dtos import RegisterDTO


class UserRepository(Protocol):
    """Contrato para operações de usuário que os Use Cases devem depender."""

    def create(self, data: RegisterDTO) -> User:
        """Cria e retorna um usuário a partir de RegisterDTO."""
        ...

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retorna usuário por id ou None."""
        ...

    def get_by_username(self, username: str) -> Optional[User]:
        """Retorna usuário por username ou None."""
        ...
