from typing import Any

from features.songs.repositories.interfaces import HymnalRepository


class HymnalService:
    def __init__(self, repository: HymnalRepository) -> None:
        self._repository = repository

    def list_hymns(self) -> list[dict[str, Any]]:
        """Return all hymns ordered by number.

        >>> service.list_hymns()
        [{'number': '1', 'title': 'First', 'lyrics': [...]}, ...]
        """
        return self._repository.list_all_hymns()
