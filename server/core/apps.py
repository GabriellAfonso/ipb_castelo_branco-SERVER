from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Shared infrastructure, and the models genuinely used by more than one feature.

    `core` became an installed app in feature 007, when two features needed the same
    church service catalogue and the constitution forbids them importing each other.
    Only entities used by two or more features belong here.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"
