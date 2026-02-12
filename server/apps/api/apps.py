from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'apps.api'

    def ready(self):
        from config.dependencies import Container
        container = Container()

        container.init_resources()
        container.wire(packages=["apps.api"])
