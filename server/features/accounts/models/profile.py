from django.db import models
from features.accounts.models.user import User
from features.accounts.validators import is_valid_username


def profile_photo_path(instance: "Profile", filename: str) -> str:
    """Build the storage path. ``filename`` already carries the validated extension.

    Falls back to the user id when the username predates the username rules: those rows
    exist, and their usernames may hold path separators or "..".

    >>> profile_photo_path(profile, "profile_picture.png")
    'profiles/ana.paula/profile_picture.png'
    """
    username = instance.user.username
    folder = username if is_valid_username(username) else str(instance.user.pk)
    return f"profiles/{folder}/{filename}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    name = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to=profile_photo_path, null=True, blank=True)
    active = models.BooleanField(default=True)
    is_member = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name
