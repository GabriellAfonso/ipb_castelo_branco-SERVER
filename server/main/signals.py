from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from main.models.profile import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            name=f"{instance.first_name} {instance.last_name}".strip().lower()
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
