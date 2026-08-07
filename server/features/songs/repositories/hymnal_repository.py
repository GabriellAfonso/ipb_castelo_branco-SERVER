from typing import Any

from features.songs.hymn_numbering import hymn_sort_key
from features.songs.models.hymnal import Hymn


class DjangoHymnalRepository:
    """Hymnal repository using Django ORM."""

    def list_all_hymns(self) -> list[dict[str, Any]]:
        """Return all hymns as dicts, ordered by numeric prefix of number.

        Sorted in Python rather than by the database. The ordering needs the numeric
        prefix of a string column, which used to mean a `REGEXP_REPLACE` annotation —
        PostgreSQL-only, and the reason this endpoint's tests were skipped on the
        SQLite test settings and so never ran in CI. The hymnal is ~400 rows and the
        expression was never indexable, so nothing is lost by sorting here.

        ``id`` is included because the hymn view history ingest endpoint keys events
        on ``hymn_id``. Without it the app holds only ``number``, a string, and cannot
        build a valid event at all.

        >>> repo.list_all_hymns()
        [{'id': 1, 'number': '1', 'title': 'First', 'lyrics': [...]}, ...]
        """
        rows: list[dict[str, Any]] = [
            dict(row) for row in Hymn.objects.values("id", "number", "title", "lyrics")
        ]
        return sorted(rows, key=lambda row: hymn_sort_key(str(row["number"])))
