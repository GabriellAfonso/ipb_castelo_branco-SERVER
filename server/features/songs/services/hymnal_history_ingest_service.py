"""Ingest use case for hymn view events."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from django.db import transaction

from core.domain.exceptions import BatchTooLargeError
from core.time.clock import Clock
from features.songs.hymnal_history_dtos import HymnViewEventInput, IngestResultDTO
from features.songs.models.hymnal_history import HymnalHistorySettings, HymnalViewEvent
from features.songs.repositories.interfaces import HymnalHistoryRepository
from features.songs.services.hymnal_history_ingest_rules import (
    BatchDecision,
    build_collapse_index,
    decide_batch,
)

logger = logging.getLogger(__name__)


class HymnalHistoryIngestService:
    """Stores a batch of hymn views, idempotently and without per-event queries."""

    def __init__(self, repository: HymnalHistoryRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def ingest(
        self,
        events: list[HymnViewEventInput],
        user_id: UUID | None = None,
    ) -> IngestResultDTO:
        """Store the events that should be stored and answer for every one of them.

        Every submitted id comes back in exactly one of ``accepted`` or ``rejected``,
        so nothing can get stuck retrying forever.

        >>> service.ingest([event], user_id=None)
        IngestResultDTO(accepted=[UUID('...')], rejected=[])
        """
        settings = self._repository.get_settings()

        if len(events) > settings.max_batch_size:
            raise BatchTooLargeError(len(events), settings.max_batch_size)

        if not events:
            return IngestResultDTO(accepted=[], rejected=[])

        decision = self._decide(events, settings)
        self._persist(decision.to_store, user_id)
        self._log_outcome(len(events), decision)

        return IngestResultDTO(accepted=decision.accepted, rejected=decision.rejected)

    def _decide(
        self,
        events: list[HymnViewEventInput],
        settings: HymnalHistorySettings,
    ) -> BatchDecision:
        """Run the three bulk reads, then apply the pure rules."""
        known_ids = self._repository.get_existing_client_event_ids(
            [e.client_event_id for e in events]
        )
        known_hymn_ids = self._repository.get_existing_hymn_ids({e.hymn_id for e in events})
        candidates = self._fetch_collapse_candidates(events, settings.collapse_window_minutes)

        return decide_batch(
            events=events,
            known_client_event_ids=known_ids,
            collapse_index=build_collapse_index(candidates),
            known_hymn_ids=known_hymn_ids,
            now=self._clock.now(),
            max_past_days=settings.max_past_days,
            future_tolerance_minutes=settings.future_tolerance_minutes,
            collapse_window_minutes=settings.collapse_window_minutes,
        )

    def _fetch_collapse_candidates(
        self,
        events: list[HymnViewEventInput],
        collapse_window_minutes: int,
    ) -> list[tuple[int, str, datetime]]:
        """One query covering the whole batch, bounded by its widest possible window."""
        pairs = {(e.hymn_id, e.device_id) for e in events}
        moments = [e.viewed_at for e in events]
        window = timedelta(minutes=collapse_window_minutes)
        return self._repository.get_collapse_candidates(
            pairs, min(moments) - window, max(moments) + window
        )

    def _persist(self, to_store: list[HymnViewEventInput], user_id: UUID | None) -> None:
        if not to_store:
            return
        rows = [
            HymnalViewEvent(
                client_event_id=event.client_event_id,
                hymn_id=event.hymn_id,
                user_id=user_id,
                device_id=event.device_id,
                viewed_at=event.viewed_at,
                duration_seconds=event.duration_seconds,
                app_version=event.app_version,
                platform=event.platform,
            )
            for event in to_store
        ]
        with transaction.atomic():
            self._repository.bulk_create_events(rows)

    def _log_outcome(self, received: int, decision: BatchDecision) -> None:
        """One summary line per request — not one per event."""
        reason_counts: dict[str, int] = {}
        for item in decision.rejected:
            reason_counts[item.reason] = reason_counts.get(item.reason, 0) + 1

        logger.info(
            "hymnal_history_ingest",
            extra={
                "received": received,
                "stored": len(decision.to_store),
                "deduplicated": decision.duplicated_count,
                "collapsed": decision.collapsed_count,
                "rejected": len(decision.rejected),
                "rejection_reasons": reason_counts,
            },
        )
