import pytest
from unittest.mock import MagicMock

from features.accounts.models.user import User
from features.accounts.services.profile_service import ProfileService


@pytest.fixture
def mock_profile_repo() -> MagicMock:
    repo = MagicMock()
    profile = MagicMock()
    profile.photo = None
    repo.get_or_create.return_value = (profile, False)
    return repo


@pytest.fixture
def service(mock_profile_repo: MagicMock) -> ProfileService:
    return ProfileService(profile_repository=mock_profile_repo)


@pytest.fixture
def mock_user() -> MagicMock:
    return MagicMock(spec=User)


def test_get_profile(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    profile = service.get_profile(mock_user)

    mock_profile_repo.get_or_create.assert_called_once_with(mock_user)
    assert profile is mock_profile_repo.get_or_create.return_value[0]


def test_update_profile(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    service.update_profile(mock_user, name="New Name")

    mock_profile_repo.get_or_create.assert_called_once_with(mock_user)
    mock_profile_repo.update.assert_called_once()
    call_kwargs = mock_profile_repo.update.call_args
    assert call_kwargs[1]["name"] == "New Name"


def test_upload_photo_deletes_old_first(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    profile = mock_profile_repo.get_or_create.return_value[0]
    profile.photo = "old.jpg"  # has existing photo

    service.upload_photo(mock_user, "new.jpg", b"content")

    mock_profile_repo.delete_photo.assert_called_once_with(profile)
    mock_profile_repo.save_photo.assert_called_once_with(profile, "new.jpg", b"content")


def test_upload_photo_no_old_photo(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    profile = mock_profile_repo.get_or_create.return_value[0]
    profile.photo = None

    service.upload_photo(mock_user, "new.jpg", b"content")

    mock_profile_repo.delete_photo.assert_not_called()
    mock_profile_repo.save_photo.assert_called_once()


def test_delete_photo(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    service.delete_photo(mock_user)

    mock_profile_repo.delete_photo.assert_called_once()
