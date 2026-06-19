from datetime import date

from django.db import transaction

from core.domain.exceptions import SongsNotFoundError
from core.metrics import SONG_PLAYS_REGISTERED_COUNTER
from features.songs.dtos import PlayInput
from features.songs.models.song import Played
from features.songs.repositories.interfaces import SongRepository


class RegisterPlaysService:
    def __init__(self, repository: SongRepository) -> None:
        self._repository = repository

    def register(self, play_date: date, plays: list[PlayInput]) -> int:
        """Validate songs exist and bulk-create Played records.

        >>> service.register(date(2026, 3, 15), [PlayInput(song_id=1, position=1, tone="G")])
        1
        """
        song_ids = {p.song_id for p in plays}
        songs_by_id = self._repository.get_songs_in_bulk(song_ids)

        missing = sorted(sid for sid in song_ids if sid not in songs_by_id)
        if missing:
            raise SongsNotFoundError(missing)

        to_create = [
            Played(
                song=songs_by_id[p.song_id],
                date=play_date,
                tone=p.tone,
                position=p.position,
            )
            for p in plays
        ]

        with transaction.atomic():
            self._repository.bulk_create_played(to_create)

        SONG_PLAYS_REGISTERED_COUNTER.inc()
        return len(to_create)
