from django.apps import AppConfig


class PersistenceConfig(AppConfig):
    name = 'apps.persistence'

    def ready(self) -> None:
        import apps.persistence.signals as _
