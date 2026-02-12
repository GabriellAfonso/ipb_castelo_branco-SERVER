from typing import Optional

from apps.persistence.models.profile import User
from core.application.dtos.auth_dtos import RegisterDTO
from core.domain.interfaces.repositories.user_repository import UserRepository


class DjangoUserRepository(UserRepository):
    """Implementação do UserRepository usando Django ORM."""

    def create(self, data: RegisterDTO) -> User:
        """
        Cria um usuário usando create_user para garantir hashing correto de senha.
        Retorna a instância criada.
        """
        # Recomenda-se que o modelo User tenha o manager create_user (padrão do Django)
        if data:
            user = User.objects.create_user(
                username=data.username, password=data.password,
                first_name=data.first_name, last_name=data.last_name)
        else:
            user = User.objects.create_user(
                username=data.username, password=data.password)
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return User.objects.filter(id=user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return User.objects.filter(username=username).first()
