"""Pure decision rules for ingesting hymn view events.

No ORM, no HTTP, no clock of its own — everything is passed in. These functions hold
the rules that are easiest to get subtly wrong (idempotency, collapse, clock skew),
so they are unit-testable without a database.
"""

from datetime import datetime, timedelta
from uuid import UUID

from features.songs.hymnal_history_dtos import (
    REASON_UNKNOWN_HYMN,
    REASON_VIEWED_AT_IN_FUTURE,
    REASON_VIEWED_AT_TOO_OLD,
    HymnViewEventInput,
    RejectedEventDTO,
)

# (hymn_id, device_id) -> the viewed_at moments already known for that pair
CollapseIndex = dict[tuple[int, str], list[datetime]]


class BatchDecision:
    """What to do with each event in a batch.

    ``accepted`` is everything the app may delete locally — stored, duplicated or
    collapsed alike. ``to_store`` is the subset that actually becomes a row.
    """

    def __init__(self) -> None:
        self.to_store: list[HymnViewEventInput] = []
        self.accepted: list[UUID] = []
        self.rejected: list[RejectedEventDTO] = []
        self.duplicated_count: int = 0
        self.collapsed_count: int = 0


def rejection_reason(
    event: HymnViewEventInput,
    now: datetime,
    known_hymn_ids: set[int],
    max_past_days: int,
    future_tolerance_minutes: int,
) -> str | None:
    """Return the rejection code for an event, or ``None`` if it is acceptable.

    ``duration_seconds`` is deliberately not checked against ``min_seconds_to_count``:
    that threshold belongs to the client, and a device syncing buffered events may
    still hold an older config value.

    >>> rejection_reason(event, now, {1}, 90, 5)
    None
    """
    if event.hymn_id not in known_hymn_ids:
        return REASON_UNKNOWN_HYMN
    if event.viewed_at > now + timedelta(minutes=future_tolerance_minutes):
        return REASON_VIEWED_AT_IN_FUTURE
    if event.viewed_at < now - timedelta(days=max_past_days):
        return REASON_VIEWED_AT_TOO_OLD
    return None


def collapses_against(
    moment: datetime,
    known_moments: list[datetime],
    collapse_window_minutes: int,
) -> bool:
    """True when ``moment`` falls within the collapse window of any known moment.

    Measured in either direction: an event arriving slightly *before* a stored one
    is the same view just as much as one arriving after.

    >>> collapses_against(t, [t - timedelta(minutes=4)], 10)
    True
    """
    window = timedelta(minutes=collapse_window_minutes)
    return any(abs(moment - known) <= window for known in known_moments)


def decide_batch(
    events: list[HymnViewEventInput],
    known_client_event_ids: set[UUID],
    collapse_index: CollapseIndex,
    known_hymn_ids: set[int],
    now: datetime,
    max_past_days: int,
    future_tolerance_minutes: int,
    collapse_window_minutes: int,
) -> BatchDecision:
    """Decide the fate of every event in a batch.

    Events are processed oldest first and the collapse index grows as decisions are
    made, so two events in the *same* request collapse against each other and not
    only against what is already stored.

    >>> decide_batch([event], set(), {}, {1}, now, 90, 5, 10).accepted
    [UUID('...')]
    """
    decision = BatchDecision()
    seen_in_batch: set[UUID] = set()

    for event in sorted(events, key=lambda e: e.viewed_at):
        if (
            event.client_event_id in known_client_event_ids
            or event.client_event_id in seen_in_batch
        ):
            decision.accepted.append(event.client_event_id)
            decision.duplicated_count += 1
            continue

        seen_in_batch.add(event.client_event_id)

        reason = rejection_reason(
            event, now, known_hymn_ids, max_past_days, future_tolerance_minutes
        )
        if reason is not None:
            decision.rejected.append(
                RejectedEventDTO(client_event_id=event.client_event_id, reason=reason)
            )
            continue

        key = (event.hymn_id, event.device_id)
        if collapses_against(event.viewed_at, collapse_index.get(key, []), collapse_window_minutes):
            decision.accepted.append(event.client_event_id)
            decision.collapsed_count += 1
            continue

        collapse_index.setdefault(key, []).append(event.viewed_at)
        decision.to_store.append(event)
        decision.accepted.append(event.client_event_id)

    return decision


def build_collapse_index(rows: list[tuple[int, str, datetime]]) -> CollapseIndex:
    """Group stored (hymn_id, device_id, viewed_at) rows by their collapse key.

    >>> build_collapse_index([(1, "dev-a", moment)])
    {(1, 'dev-a'): [datetime.datetime(...)]}
    """
    index: CollapseIndex = {}
    for hymn_id, device_id, viewed_at in rows:
        index.setdefault((hymn_id, device_id), []).append(viewed_at)
    return index
