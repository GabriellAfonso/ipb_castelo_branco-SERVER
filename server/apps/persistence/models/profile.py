from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        # TODO colocar esse user num app diferente só relacionado a autenticaçao
        # app_label = 'auth'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


def profile_photo_path(instance: "Profile", filename: str) -> str:
    ext = filename.split('.')[-1]
    return f"profiles/{instance.user.username}/profile_picture.{ext}"


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    name = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(
        upload_to=profile_photo_path, null=True, blank=True)
    active = models.BooleanField(default=True)
    is_member = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name
