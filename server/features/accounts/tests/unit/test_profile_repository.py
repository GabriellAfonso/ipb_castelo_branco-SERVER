import pytest

from features.accounts.models.profile import Profile
from features.accounts.models.user import User
from features.accounts.repositories.profile_repository import DjangoProfileRepository


@pytest.fixture
def repo() -> DjangoProfileRepository:
    return DjangoProfileRepository()


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user(
        username="profuser", password="testpass123", first_name="Prof", last_name="User"
    )


@pytest.mark.django_db
def test_get_or_create_creates_profile(repo: DjangoProfileRepository, user: User) -> None:
    # Signal already creates profile, so delete it first to test creation
    Profile.objects.filter(user=user).delete()
    profile, created = repo.get_or_create(user)
    assert created is True
    assert profile.user == user


@pytest.mark.django_db
def test_get_or_create_returns_existing(repo: DjangoProfileRepository, user: User) -> None:
    # Signal creates profile on user creation
    profile, created = repo.get_or_create(user)
    assert created is False
    assert profile.user == user


@pytest.mark.django_db
def test_save_photo(repo: DjangoProfileRepository, user: User) -> None:
    profile = user.profile
    repo.save_photo(profile, "test.jpg", b"fake-image-content")
    profile.refresh_from_db()
    assert profile.photo is not None
    assert profile.photo.name.startswith("profiles/profuser/profile_picture")


@pytest.mark.django_db
def test_delete_photo(repo: DjangoProfileRepository, user: User) -> None:
    profile = user.profile
    repo.save_photo(profile, "test.jpg", b"fake-image-content")
    repo.delete_photo(profile)
    profile.refresh_from_db()
    assert not profile.photo


@pytest.mark.django_db
def test_delete_photo_noop_when_no_photo(repo: DjangoProfileRepository, user: User) -> None:
    profile = user.profile
    repo.delete_photo(profile)  # should not raise
    profile.refresh_from_db()
    assert not profile.photo


@pytest.mark.django_db
def test_update_fields(repo: DjangoProfileRepository, user: User) -> None:
    profile = user.profile
    updated = repo.update(profile, name="New Name")
    assert updated.name == "New Name"
    profile.refresh_from_db()
    assert profile.name == "New Name"
