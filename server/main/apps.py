from django.apps import AppConfig


class MainConfig(AppConfig):
    name = 'main'

    def ready(self) -> None:
        import main.signals as _
