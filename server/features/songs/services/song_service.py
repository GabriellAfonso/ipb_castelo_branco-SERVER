import random
from datetime import date, timedelta
from typing import Any, NamedTuple

from django.db.models import QuerySet
from django.utils.timezone import now

from core.domain.exceptions import ChordChartNotFoundError, LyricsNotFoundError
from features.songs.models.chord_chart import ChordChart
from features.songs.models.lyrics import Lyrics
from features.songs.models.song import Played, Song
from features.songs.repositories.interfaces import SongRepository


class SuggestedPlay(NamedTuple):
    played: Played
    position: int


class SongService:
    def __init__(self, repository: SongRepository) -> None:
        self._repository = repository

    def list_all_songs(self) -> QuerySet[Song]:
        return self._repository.list_all_songs()

    def list_all_played(self) -> QuerySet[Played]:
        return self._repository.list_all_played()

    def top_songs(self) -> list[dict[str, Any]]:
        return self._repository.top_songs()

    def top_tones(self) -> list[dict[str, Any]]:
        return self._repository.top_tones()

    def suggest_songs(
        self,
        fixed_by_position: dict[int, int] | None = None,
    ) -> list[SuggestedPlay]:
        """Suggest songs for positions 1-4, respecting pinned positions.

        >>> service.suggest_songs({1: 42})  # pin position 1 to Played id=42
        [SuggestedPlay(played=..., position=1), ...]
        """
        fixed_by_position = fixed_by_position or {}
        three_months_ago = (now() - timedelta(days=90)).date()
        used_song_ids: set[int] = set()
        result: list[SuggestedPlay] = []

        recent_song_ids = set(self._repository.get_recent_song_ids(three_months_ago))

        if fixed_by_position:
            fixed_plays, used_song_ids = self._resolve_fixed(fixed_by_position)
            result.extend(fixed_plays)

        for position in range(1, 5):
            if position in fixed_by_position:
                continue
            play = self._pick_for_position(
                position,
                three_months_ago,
                recent_song_ids | used_song_ids,
            )
            if play:
                if play.song_id is not None:
                    used_song_ids.add(play.song_id)
                result.append(SuggestedPlay(played=play, position=position))

        result.sort(key=lambda x: x.position)
        return result

    def _resolve_fixed(
        self,
        fixed_by_position: dict[int, int],
    ) -> tuple[list[SuggestedPlay], set[int]]:
        fixed_ids = list(set(fixed_by_position.values()))
        fixed_by_id = self._repository.get_played_by_ids(fixed_ids)
        result: list[SuggestedPlay] = []
        used_song_ids: set[int] = set()

        for position, played_id in fixed_by_position.items():
            played_obj = fixed_by_id.get(played_id)
            if not played_obj:
                continue
            if played_obj.song_id is not None:
                used_song_ids.add(played_obj.song_id)
            result.append(SuggestedPlay(played=played_obj, position=position))

        return result, used_song_ids

    def _pick_for_position(
        self,
        position: int,
        before: date,
        exclude_song_ids: set[int],
    ) -> Played | None:
        qs = self._repository.get_eligible_plays(position, before, exclude_song_ids)
        if not qs.exists():
            return None
        return random.choice(list(qs))  # nosec B311

    def list_chord_charts(self) -> QuerySet[ChordChart]:
        return self._repository.list_all_chord_charts()

    def update_chord_chart_content(self, pk: int, content: str) -> ChordChart:
        """Update chord chart content by id.

        >>> service.update_chord_chart_content(1, "Am G C")
        <ChordChart: ...>
        """
        chart = self._repository.get_chord_chart_by_id(pk)
        if not chart:
            raise ChordChartNotFoundError(pk)
        chart.content = content
        self._repository.save_chord_chart(chart, ["content", "updated_at"])
        return chart

    def list_lyrics(self) -> QuerySet[Lyrics]:
        return self._repository.list_all_lyrics()

    def update_lyrics_content(self, pk: int, content: str) -> Lyrics:
        """Update lyrics content by id.

        >>> service.update_lyrics_content(1, "Amazing grace")
        <Lyrics: ...>
        """
        lyrics = self._repository.get_lyrics_by_id(pk)
        if not lyrics:
            raise LyricsNotFoundError(pk)
        lyrics.content = content
        self._repository.save_lyrics(lyrics, ["content", "updated_at"])
        return lyrics
