from datetime import date
from typing import Any, Protocol

from django.db.models import QuerySet

from features.songs.models.chord_chart import ChordChart
from features.songs.models.hymnal import Hymn
from features.songs.models.lyrics import Lyrics
from features.songs.models.song import Played, Song


class SongRepository(Protocol):
    """Contract for song persistence operations."""

    def list_all_songs(self) -> QuerySet[Song]: ...

    def list_all_played(self) -> QuerySet[Played]: ...

    def top_songs(self) -> list[dict[str, Any]]: ...

    def top_tones(self) -> list[dict[str, Any]]: ...

    def get_recent_song_ids(self, since: date) -> list[int]: ...

    def get_played_by_ids(self, ids: list[int]) -> dict[int, Played]: ...

    def get_eligible_plays(
        self,
        position: int,
        before: date,
        exclude_song_ids: set[int],
    ) -> QuerySet[Played]: ...

    def get_songs_in_bulk(self, ids: set[int]) -> dict[int, Song]: ...

    def bulk_create_played(self, items: list[Played]) -> list[Played]: ...

    def list_all_chord_charts(self) -> QuerySet[ChordChart]: ...

    def get_chord_chart_by_id(self, pk: int) -> ChordChart | None: ...

    def list_all_lyrics(self) -> QuerySet[Lyrics]: ...

    def get_lyrics_by_id(self, pk: int) -> Lyrics | None: ...

    def save_chord_chart(self, chart: ChordChart, fields: list[str]) -> None: ...

    def save_lyrics(self, lyrics: Lyrics, fields: list[str]) -> None: ...


class HymnalRepository(Protocol):
    """Contract for hymnal persistence operations."""

    def list_all_hymns(self) -> QuerySet[Hymn]: ...
