from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_auth_client, make_user
from features.songs.models.hymnal import Hymn
from features.songs.models.hymnal_history import HymnalHistorySettings, HymnalViewEvent

URL = "/api/hymnal-history/events/"


def _hymn(number: str = "50") -> Hymn:
    return Hymn.objects.create(number=number, title=f"Hino {number}", lyrics=[])


def _event(hymn_id: int, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_event_id": str(uuid4()),
        "hymn_id": hymn_id,
        "device_id": "device-a",
        "viewed_at": (timezone.now() - timedelta(minutes=5)).isoformat(),
        "duration_seconds": 47,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestIngestAuth:
    def test_anonymous_post_is_accepted_and_stored_without_a_user(self) -> None:
        hymn = _hymn()
        event = _event(hymn.id)
        resp = APIClient().post(URL, {"events": [event]}, format="json")

        assert resp.status_code == 201
        assert resp.data["accepted"] == [event["client_event_id"]]
        assert HymnalViewEvent.objects.get().user is None

    def test_authenticated_post_attributes_the_user(self) -> None:
        hymn = _hymn()
        user = make_user()
        client = make_auth_client(user)

        resp = client.post(URL, {"events": [_event(hymn.id)]}, format="json")

        assert resp.status_code == 201
        assert HymnalViewEvent.objects.get().user_id == user.id

    def test_device_id_is_required_even_when_anonymous(self) -> None:
        hymn = _hymn()
        event = _event(hymn.id)
        del event["device_id"]

        resp = APIClient().post(URL, {"events": [event]}, format="json")

        assert resp.status_code == 201
        assert resp.data["accepted"] == []
        assert resp.data["rejected"][0]["reason"] == "invalid_event"
        assert HymnalViewEvent.objects.count() == 0


@pytest.mark.django_db
class TestIngestIdempotency:
    def test_resending_the_same_batch_creates_nothing_new(self) -> None:
        hymn = _hymn()
        payload = {"events": [_event(hymn.id)]}
        client = APIClient()

        first = client.post(URL, payload, format="json")
        second = client.post(URL, payload, format="json")

        assert first.data["accepted"] == second.data["accepted"]
        assert HymnalViewEvent.objects.count() == 1

    def test_same_client_event_id_twice_in_one_batch(self) -> None:
        hymn = _hymn()
        shared = str(uuid4())
        events = [
            _event(hymn.id, client_event_id=shared),
            _event(hymn.id, client_event_id=shared, device_id="device-b"),
        ]

        resp = APIClient().post(URL, {"events": events}, format="json")

        assert resp.status_code == 201
        assert resp.data["accepted"] == [shared, shared]
        assert HymnalViewEvent.objects.count() == 1


@pytest.mark.django_db
class TestIngestCollapse:
    def test_same_hymn_and_device_inside_the_window_collapses(self) -> None:
        hymn = _hymn()
        now = timezone.now()
        events = [
            _event(hymn.id, viewed_at=(now - timedelta(minutes=10)).isoformat()),
            _event(hymn.id, viewed_at=(now - timedelta(minutes=6)).isoformat()),
        ]

        resp = APIClient().post(URL, {"events": events}, format="json")

        assert len(resp.data["accepted"]) == 2
        assert HymnalViewEvent.objects.count() == 1

    def test_beyond_the_window_both_are_stored(self) -> None:
        hymn = _hymn()
        now = timezone.now()
        events = [
            _event(hymn.id, viewed_at=(now - timedelta(minutes=40)).isoformat()),
            _event(hymn.id, viewed_at=(now - timedelta(minutes=5)).isoformat()),
        ]

        APIClient().post(URL, {"events": events}, format="json")

        assert HymnalViewEvent.objects.count() == 2

    def test_collapses_against_an_already_stored_event(self) -> None:
        hymn = _hymn()
        now = timezone.now()
        client = APIClient()

        client.post(
            URL,
            {"events": [_event(hymn.id, viewed_at=(now - timedelta(minutes=8)).isoformat())]},
            format="json",
        )
        resp = client.post(
            URL,
            {"events": [_event(hymn.id, viewed_at=(now - timedelta(minutes=5)).isoformat())]},
            format="json",
        )

        assert len(resp.data["accepted"]) == 1
        assert HymnalViewEvent.objects.count() == 1


@pytest.mark.django_db
class TestIngestPerEventRejection:
    def test_one_bad_event_does_not_block_the_rest(self) -> None:
        hymn = _hymn()
        good = _event(hymn.id)
        bad = _event(999999, device_id="device-b")

        resp = APIClient().post(URL, {"events": [good, bad]}, format="json")

        assert resp.status_code == 201
        assert resp.data["accepted"] == [good["client_event_id"]]
        assert resp.data["rejected"] == [
            {"client_event_id": bad["client_event_id"], "reason": "unknown_hymn"}
        ]
        assert HymnalViewEvent.objects.count() == 1

    def test_viewed_at_in_the_future_is_rejected(self) -> None:
        hymn = _hymn()
        event = _event(hymn.id, viewed_at=(timezone.now() + timedelta(hours=2)).isoformat())

        resp = APIClient().post(URL, {"events": [event]}, format="json")

        assert resp.data["rejected"][0]["reason"] == "viewed_at_in_future"
        assert HymnalViewEvent.objects.count() == 0

    def test_viewed_at_too_old_is_rejected(self) -> None:
        hymn = _hymn()
        event = _event(hymn.id, viewed_at=(timezone.now() - timedelta(days=120)).isoformat())

        resp = APIClient().post(URL, {"events": [event]}, format="json")

        assert resp.data["rejected"][0]["reason"] == "viewed_at_too_old"

    def test_naive_viewed_at_is_rejected_as_invalid(self) -> None:
        hymn = _hymn()
        event = _event(hymn.id, viewed_at="2026-08-09T19:30:00")

        resp = APIClient().post(URL, {"events": [event]}, format="json")

        assert resp.data["rejected"][0]["reason"] == "invalid_event"

    def test_every_event_is_answered_exactly_once(self) -> None:
        hymn = _hymn()
        events = [_event(hymn.id), _event(999999, device_id="device-b")]

        resp = APIClient().post(URL, {"events": events}, format="json")

        answered = set(resp.data["accepted"]) | {
            r["client_event_id"] for r in resp.data["rejected"]
        }
        assert answered == {e["client_event_id"] for e in events}


@pytest.mark.django_db
class TestIngestBatchEnvelope:
    def test_empty_batch_is_a_valid_no_op(self) -> None:
        resp = APIClient().post(URL, {"events": []}, format="json")

        assert resp.status_code == 201
        assert resp.data == {"accepted": [], "rejected": []}

    def test_missing_events_key_is_400(self) -> None:
        resp = APIClient().post(URL, {}, format="json")
        assert resp.status_code == 400

    def test_events_not_a_list_is_400(self) -> None:
        resp = APIClient().post(URL, {"events": "nope"}, format="json")
        assert resp.status_code == 400

    def test_batch_over_max_size_fails_as_a_whole(self) -> None:
        hymn = _hymn()
        HymnalHistorySettings.objects.create(id=1, max_batch_size=3)
        events = [_event(hymn.id, device_id=f"device-{i}") for i in range(4)]

        resp = APIClient().post(URL, {"events": events}, format="json")

        assert resp.status_code == 400
        assert resp.data["error_code"] == "VALIDATION_ERROR"
        assert "max_batch_size" in resp.data["detail"]
        assert HymnalViewEvent.objects.count() == 0


@pytest.mark.django_db
class TestIngestStoresWhatItReceives:
    def test_duration_below_the_threshold_is_still_stored(self) -> None:
        """FR-011: the client owns the threshold; a buffered event may carry an older one."""
        hymn = _hymn()
        resp = APIClient().post(
            URL, {"events": [_event(hymn.id, duration_seconds=3)]}, format="json"
        )

        assert resp.status_code == 201
        assert HymnalViewEvent.objects.get().duration_seconds == 3

    def test_optional_fields_default_to_empty(self) -> None:
        hymn = _hymn()
        APIClient().post(URL, {"events": [_event(hymn.id)]}, format="json")

        stored = HymnalViewEvent.objects.get()
        assert stored.app_version == ""
        assert stored.platform == ""

    def test_optional_fields_are_stored_when_sent(self) -> None:
        hymn = _hymn()
        APIClient().post(
            URL,
            {"events": [_event(hymn.id, app_version="1.4.2", platform="android")]},
            format="json",
        )

        stored = HymnalViewEvent.objects.get()
        assert stored.app_version == "1.4.2"
        assert stored.platform == "android"
