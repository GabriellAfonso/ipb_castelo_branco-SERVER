from typing import Any

from django.db.models import Func, IntegerField, Value
from django.db.models.functions import Cast, NullIf

from features.songs.models.hymnal import Hymn


class DjangoHymnalRepository:
    """Hymnal repository using Django ORM."""

    def list_all_hymns(self) -> list[dict[str, Any]]:
        """Return all hymns as dicts, ordered by numeric prefix of number.

        >>> repo.list_all_hymns()
        [{'number': '1', 'title': 'First', 'lyrics': [...]}, ...]
        """
        return list(
            Hymn.objects.annotate(
                number_int=Cast(
                    NullIf(
                        Func(
                            "number",
                            Value("[^0-9].*"),
                            Value(""),
                            function="REGEXP_REPLACE",
                        ),
                        Value(""),
                    ),
                    IntegerField(),
                )
            )
            .order_by("number_int", "number")
            .values("number", "title", "lyrics")
        )
