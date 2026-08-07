from datetime import datetime, timedelta, timezone as dt_timezone
from uuid import UUID, uuid4

from features.songs.hymnal_history_dtos import (
    REASON_UNKNOWN_HYMN,
    REASON_VIEWED_AT_IN_FUTURE,
    REASON_VIEWED_AT_TOO_OLD,
    HymnViewEventInput,
)
from features.songs.services.hymnal_history_ingest_rules import (
    BatchDecision,
    build_collapse_index,
    collapses_against,
    decide_batch,
    rejection_reason,
)

NOW = datetime(2026, 8, 9, 22, 0, tzinfo=dt_timezone.utc)
KNOWN_HYMNS = {1, 2}


def _event(
    hymn_id: int = 1,
    device_id: str = "device-a",
    minutes_ago: int = 0,
    client_event_id: UUID | None = None,
    duration_seconds: int = 40,
) -> HymnViewEventInput:
    return HymnViewEventInput(
        client_event_id=client_event_id or uuid4(),
        hymn_id=hymn_id,
        device_id=device_id,
        viewed_at=NOW - timedelta(minutes=minutes_ago),
        duration_seconds=duration_seconds,
    )


def _decide(events: list[HymnViewEventInput], **overrides: object) -> BatchDecision:
    kwargs: dict[str, object] = {
        "events": events,
        "known_client_event_ids": set(),
        "collapse_index": {},
        "known_hymn_ids": KNOWN_HYMNS,
        "now": NOW,
        "max_past_days": 90,
        "future_tolerance_minutes": 5,
        "collapse_window_minutes": 10,
    }
    kwargs.update(overrides)
    return decide_batch(**kwargs)  # type: ignore[arg-type]


class TestRejectionReason:
    def test_valid_event_has_no_reason(self) -> None:
        assert rejection_reason(_event(), NOW, KNOWN_HYMNS, 90, 5) is None

    def test_unknown_hymn(self) -> None:
        assert rejection_reason(_event(hymn_id=999), NOW, KNOWN_HYMNS, 90, 5) == REASON_UNKNOWN_HYMN

    def test_viewed_at_beyond_future_tolerance(self) -> None:
        event = _event(minutes_ago=-6)
        assert rejection_reason(event, NOW, KNOWN_HYMNS, 90, 5) == REASON_VIEWED_AT_IN_FUTURE

    def test_viewed_at_inside_future_tolerance_is_accepted(self) -> None:
        event = _event(minutes_ago=-4)
        assert rejection_reason(event, NOW, KNOWN_HYMNS, 90, 5) is None

    def test_viewed_at_older_than_max_past_days(self) -> None:
        event = _event(minutes_ago=60 * 24 * 91)
        assert rejection_reason(event, NOW, KNOWN_HYMNS, 90, 5) == REASON_VIEWED_AT_TOO_OLD

    def test_duration_below_threshold_is_not_a_rejection(self) -> None:
        """FR-011: the client owns min_seconds_to_count; the backend stores what it gets."""
        assert rejection_reason(_event(duration_seconds=3), NOW, KNOWN_HYMNS, 90, 5) is None


class TestCollapsesAgainst:
    def test_inside_window_in_either_direction(self) -> None:
        assert collapses_against(NOW, [NOW - timedelta(minutes=4)], 10) is True
        assert collapses_against(NOW, [NOW + timedelta(minutes=4)], 10) is True

    def test_outside_window(self) -> None:
        assert collapses_against(NOW, [NOW - timedelta(minutes=11)], 10) is False

    def test_exactly_at_the_boundary_collapses(self) -> None:
        assert collapses_against(NOW, [NOW - timedelta(minutes=10)], 10) is True

    def test_no_known_moments(self) -> None:
        assert collapses_against(NOW, [], 10) is False


class TestBuildCollapseIndex:
    def test_groups_by_hymn_and_device(self) -> None:
        index = build_collapse_index([(1, "a", NOW), (1, "a", NOW), (2, "a", NOW)])
        assert len(index[(1, "a")]) == 2
        assert len(index[(2, "a")]) == 1


class TestDecideBatch:
    def test_valid_event_is_stored_and_accepted(self) -> None:
        event = _event()
        decision = _decide([event])
        assert decision.to_store == [event]
        assert decision.accepted == [event.client_event_id]
        assert decision.rejected == []

    def test_known_client_event_id_is_accepted_but_not_stored(self) -> None:
        event = _event()
        decision = _decide([event], known_client_event_ids={event.client_event_id})
        assert decision.to_store == []
        assert decision.accepted == [event.client_event_id]
        assert decision.duplicated_count == 1

    def test_same_client_event_id_twice_in_one_batch(self) -> None:
        shared = uuid4()
        events = [_event(client_event_id=shared), _event(client_event_id=shared, minutes_ago=30)]
        decision = _decide(events)
        assert len(decision.to_store) == 1
        assert decision.accepted == [shared, shared]

    def test_collapses_against_stored_event(self) -> None:
        event = _event(minutes_ago=0)
        index = {(1, "device-a"): [NOW - timedelta(minutes=4)]}
        decision = _decide([event], collapse_index=index)
        assert decision.to_store == []
        assert decision.accepted == [event.client_event_id]
        assert decision.collapsed_count == 1

    def test_collapses_within_the_same_batch(self) -> None:
        """Left the hymn and came back 4 minutes later, both synced together."""
        first = _event(minutes_ago=10)
        second = _event(minutes_ago=6)
        decision = _decide([first, second])
        assert decision.to_store == [first]
        assert set(decision.accepted) == {first.client_event_id, second.client_event_id}
        assert decision.collapsed_count == 1

    def test_does_not_collapse_beyond_the_window(self) -> None:
        first = _event(minutes_ago=30)
        second = _event(minutes_ago=10)
        decision = _decide([first, second])
        assert len(decision.to_store) == 2

    def test_different_devices_do_not_collapse(self) -> None:
        first = _event(device_id="device-a")
        second = _event(device_id="device-b", minutes_ago=1)
        decision = _decide([first, second])
        assert len(decision.to_store) == 2

    def test_different_hymns_do_not_collapse(self) -> None:
        first = _event(hymn_id=1)
        second = _event(hymn_id=2, minutes_ago=1)
        decision = _decide([first, second])
        assert len(decision.to_store) == 2

    def test_one_bad_event_does_not_block_the_rest(self) -> None:
        good = _event()
        bad = _event(hymn_id=999, minutes_ago=1)
        decision = _decide([good, bad])
        assert decision.to_store == [good]
        assert decision.accepted == [good.client_event_id]
        assert len(decision.rejected) == 1
        assert decision.rejected[0].reason == REASON_UNKNOWN_HYMN

    def test_every_event_is_answered_exactly_once(self) -> None:
        events = [_event(), _event(hymn_id=999, minutes_ago=20), _event(minutes_ago=40)]
        decision = _decide(events)
        answered = set(decision.accepted) | {r.client_event_id for r in decision.rejected}
        assert answered == {e.client_event_id for e in events}

    def test_short_duration_is_stored(self) -> None:
        event = _event(duration_seconds=3)
        decision = _decide([event])
        assert decision.to_store == [event]
