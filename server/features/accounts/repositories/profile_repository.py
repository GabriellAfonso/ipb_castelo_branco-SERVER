from django.core.files.base import ContentFile

from features.accounts.models.profile import Profile
from features.accounts.models.user import User
from features.accounts.repositories.interfaces import ProfileRepository


class DjangoProfileRepository(ProfileRepository):
    """Implementação do ProfileRepository usando Django ORM."""

    def get_or_create(self, user: User) -> tuple[Profile, bool]:
        return Profile.objects.get_or_create(user=user)

    def save_photo(self, profile: Profile, filename: str, content: bytes) -> None:
        profile.photo.save(filename, ContentFile(content), save=True)

    def delete_photo(self, profile: Profile) -> None:
        if profile.photo:
            profile.photo.delete(save=False)
            profile.photo = None
            profile.save(update_fields=["photo"])

    def update(self, profile: Profile, **fields: object) -> Profile:
        for key, value in fields.items():
            setattr(profile, key, value)
        profile.save(update_fields=list(fields.keys()))
        return profile
