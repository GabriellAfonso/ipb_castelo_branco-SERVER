from typing import IO

from core.files.image_validation import detect_image_extension
from features.accounts.models.profile import Profile
from features.accounts.models.user import User
from features.accounts.repositories.interfaces import ProfileRepository


class ProfileService:
    def __init__(self, profile_repository: ProfileRepository) -> None:
        self._profile_repo = profile_repository

    def get_profile(self, user: User) -> Profile:
        profile, _ = self._profile_repo.get_or_create(user)
        return profile

    def update_profile(self, user: User, **fields: object) -> Profile:
        profile, _ = self._profile_repo.get_or_create(user)
        return self._profile_repo.update(profile, **fields)

    def upload_photo(self, user: User, upload: IO[bytes]) -> Profile:
        """Replace the user's photo, refusing anything that is not a decodable image.

        Validation runs before the existing photo is deleted, so a rejected upload
        cannot destroy the picture the user already had.

        >>> service.upload_photo(user, open("avatar.png", "rb"))
        """
        extension = detect_image_extension(upload)

        profile, _ = self._profile_repo.get_or_create(user)
        if profile.photo:
            self._profile_repo.delete_photo(profile)
        self._profile_repo.save_photo(profile, extension, upload)
        profile.refresh_from_db()
        return profile

    def delete_photo(self, user: User) -> None:
        profile, _ = self._profile_repo.get_or_create(user)
        self._profile_repo.delete_photo(profile)
