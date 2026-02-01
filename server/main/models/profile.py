from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    name = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to="profiles/", null=True, blank=True)
    active = models.BooleanField(default=True)
    is_member = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
