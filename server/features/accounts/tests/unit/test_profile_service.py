from io import BytesIO
from unittest.mock import MagicMock

import pytest
from PIL import Image

from core.domain.exceptions import ValidationError

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


def _png_upload(name: str = "avatar.png") -> BytesIO:
    """A real, decodable PNG — the service now rejects anything else."""
    buffer = BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    buffer.seek(0)
    buffer.name = name
    return buffer


def test_upload_photo_deletes_old_first(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    profile = mock_profile_repo.get_or_create.return_value[0]
    profile.photo = "old.jpg"  # has existing photo
    upload = _png_upload()

    service.upload_photo(mock_user, upload)

    mock_profile_repo.delete_photo.assert_called_once_with(profile)
    mock_profile_repo.save_photo.assert_called_once_with(profile, "png", upload)


def test_upload_photo_no_old_photo(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    profile = mock_profile_repo.get_or_create.return_value[0]
    profile.photo = None

    service.upload_photo(mock_user, _png_upload())

    mock_profile_repo.delete_photo.assert_not_called()
    mock_profile_repo.save_photo.assert_called_once()


def test_upload_photo_derives_extension_from_content_not_filename(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    """Regression: a PNG named ``evil.html`` must never be stored as HTML."""
    mock_profile_repo.get_or_create.return_value[0].photo = None

    service.upload_photo(mock_user, _png_upload("evil.html"))

    assert mock_profile_repo.save_photo.call_args[0][1] == "png"


def test_upload_photo_rejects_non_image_without_touching_the_old_photo(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    """Regression: a rejected upload must not destroy the picture the user had."""
    mock_profile_repo.get_or_create.return_value[0].photo = "old.jpg"

    with pytest.raises(ValidationError, match="não é uma imagem"):
        service.upload_photo(mock_user, BytesIO(b"<html>not an image</html>"))

    mock_profile_repo.delete_photo.assert_not_called()
    mock_profile_repo.save_photo.assert_not_called()


def test_delete_photo(
    service: ProfileService, mock_profile_repo: MagicMock, mock_user: MagicMock
) -> None:
    service.delete_photo(mock_user)

    mock_profile_repo.delete_photo.assert_called_once()
