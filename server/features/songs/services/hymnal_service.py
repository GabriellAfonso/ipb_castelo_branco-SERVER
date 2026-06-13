from django.db.models import QuerySet

from features.songs.models.hymnal import Hymn
from features.songs.repositories.interfaces import HymnalRepository


class HymnalService:
    def __init__(self, repository: HymnalRepository) -> None:
        self._repository = repository

    def list_hymns(self) -> QuerySet[Hymn]:
        """Return all hymns ordered by number.

        >>> service.list_hymns()
        <QuerySet [<Hymn: 1 - First>, <Hymn: 2 - Second>]>
        """
        return self._repository.list_all_hymns()
