from typing import Any

from django.db.models import Func, IntegerField, Value
from django.db.models.functions import Cast, NullIf

from features.songs.models.hymnal import Hymn


class DjangoHymnalRepository:
    """Hymnal repository using Django ORM."""

    def list_all_hymns(self) -> list[dict[str, Any]]:
        """Return all hymns as dicts, ordered by numeric prefix of number.

        ``id`` is included because the hymn view history ingest endpoint keys events
        on ``hymn_id``. Without it the app holds only ``number``, a string, and cannot
        build a valid event at all.

        >>> repo.list_all_hymns()
        [{'id': 1, 'number': '1', 'title': 'First', 'lyrics': [...]}, ...]
        """
        qs = (
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
            .values("id", "number", "title", "lyrics")
        )
        return [dict(row) for row in qs]
