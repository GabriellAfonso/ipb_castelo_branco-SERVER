import json
from pathlib import Path
from typing import Protocol

from features.bible.dtos import BibleBook

_DATA_DIR = Path(__file__).parent / "data"


class BibleRepository(Protocol):
    """Contract for Bible data access."""

    def list_versions(self) -> list[str]: ...

    def get_version(self, name: str) -> list[BibleBook] | None: ...


class JsonFileBibleRepository:
    """Loads Bible data from static JSON files at construction time."""

    def __init__(self) -> None:
        self._bibles: dict[str, list[BibleBook]] = {}
        self._load()

    def _load(self) -> None:
        for path in _DATA_DIR.glob("*.json"):
            with path.open(encoding="utf-8") as f:
                raw: list[dict[str, object]] = json.load(f)
            self._bibles[path.stem] = [BibleBook.model_validate(book) for book in raw]

    def list_versions(self) -> list[str]:
        return sorted(self._bibles.keys())

    def get_version(self, name: str) -> list[BibleBook] | None:
        books = self._bibles.get(name)
        if books is None:
            return None
        return books
