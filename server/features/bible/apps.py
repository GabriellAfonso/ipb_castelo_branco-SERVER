from django.apps import AppConfig


class BibleConfig(AppConfig):
    name = "features.bible"

    def ready(self) -> None:
        from features.bible.loader import load_bibles

        load_bibles()
