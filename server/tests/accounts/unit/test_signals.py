import os
import tempfile

import pytest
from django.test import override_settings

from tests.conftest import make_user


@pytest.mark.django_db
def test_profile_created_on_user_creation() -> None:
    user = make_user(username="siguser", password="pass123", first_name="Sig", last_name="User")
    assert hasattr(user, "profile")
    assert user.profile.name == "Sig User"


@pytest.mark.django_db
def test_profile_name_title_cased() -> None:
    user = make_user(username="titlecase", password="pass123", first_name="john", last_name="doe")
    assert user.profile.name == "John Doe"


@pytest.mark.django_db
def test_old_photo_deleted_on_change() -> None:
    with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
        user = make_user(username="photoswap", password="pass123")
        profile = user.profile

        # Simulate saving a photo file
        from django.core.files.base import ContentFile

        profile.photo.save("old.jpg", ContentFile(b"old-photo-data"), save=True)
        old_path = profile.photo.path
        assert os.path.isfile(old_path)

        # Replace with new photo
        profile.photo.save("new.jpg", ContentFile(b"new-photo-data"), save=True)
        assert not os.path.isfile(old_path), "Old photo file should be deleted from disk"
        assert os.path.isfile(profile.photo.path)


@pytest.mark.django_db
def test_photo_deleted_on_profile_delete() -> None:
    with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
        user = make_user(username="photodel", password="pass123")
        profile = user.profile

        from django.core.files.base import ContentFile

        profile.photo.save("todelete.jpg", ContentFile(b"photo-data"), save=True)
        photo_path = profile.photo.path
        assert os.path.isfile(photo_path)

        profile.delete()
        assert not os.path.isfile(photo_path), (
            "Photo file should be deleted when profile is deleted"
        )
