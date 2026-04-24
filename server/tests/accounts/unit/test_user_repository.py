import pytest

from features.accounts.models.user import User
from features.accounts.repositories.user_repository import DjangoUserRepository
from features.core.application.dtos.auth_dtos import RegisterDTO


@pytest.fixture
def repo() -> DjangoUserRepository:
    return DjangoUserRepository()


@pytest.fixture
def sample_dto() -> RegisterDTO:
    return RegisterDTO(
        username="repouser",
        password="securepass123",
        first_name="Repo",
        last_name="User",
    )


@pytest.mark.django_db
def test_create_returns_user_with_correct_data(
    repo: DjangoUserRepository, sample_dto: RegisterDTO
) -> None:
    user = repo.create(sample_dto)
    assert isinstance(user, User)
    assert user.username == "repouser"
    assert user.first_name == "Repo"
    assert user.last_name == "User"
    assert user.check_password("securepass123")


@pytest.mark.django_db
def test_get_by_id_returns_user(repo: DjangoUserRepository, sample_dto: RegisterDTO) -> None:
    created = repo.create(sample_dto)
    found = repo.get_by_id(created.id)
    assert found is not None
    assert found.id == created.id


@pytest.mark.django_db
def test_get_by_id_returns_none_for_unknown(repo: DjangoUserRepository) -> None:
    import uuid

    assert repo.get_by_id(uuid.uuid4()) is None


@pytest.mark.django_db
def test_get_by_username_returns_user(repo: DjangoUserRepository, sample_dto: RegisterDTO) -> None:
    repo.create(sample_dto)
    found = repo.get_by_username("repouser")
    assert found is not None
    assert found.username == "repouser"


@pytest.mark.django_db
def test_get_by_username_returns_none_for_unknown(repo: DjangoUserRepository) -> None:
    assert repo.get_by_username("nonexistent") is None
