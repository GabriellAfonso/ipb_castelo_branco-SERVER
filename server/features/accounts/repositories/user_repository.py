from typing import Optional
from uuid import UUID

from features.accounts.models.user import User
from core.application.dtos.auth_dtos import RegisterDTO
from features.accounts.repositories.interfaces import UserRepository


class DjangoUserRepository(UserRepository):
    """Implementação do UserRepository usando Django ORM."""

    def create(self, data: RegisterDTO) -> User:
        return User.objects.create_user(
            username=data.username,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
        )

    def create_google_user(
        self, email: str, username: str, first_name: str, last_name: str
    ) -> User:
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        return user

    def get_by_id(self, user_id: UUID | str) -> Optional[User]:
        return User.objects.filter(id=user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return User.objects.filter(username=username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return User.objects.filter(email=email).first()

    def username_exists(self, username: str) -> bool:
        return User.objects.filter(username=username).exists()

    def generate_unique_username(self, base: str) -> str:
        username = base
        counter = 1
        while self.username_exists(username):
            username = f"{base}{counter}"
            counter += 1
        return username
