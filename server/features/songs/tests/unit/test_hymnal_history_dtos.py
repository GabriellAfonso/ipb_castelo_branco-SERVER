from datetime import datetime, timezone as dt_timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from features.songs.hymnal_history_dtos import HymnViewEventInput

AWARE = datetime(2026, 8, 9, 19, 32, tzinfo=dt_timezone.utc)


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "client_event_id": uuid4(),
        "hymn_id": 1,
        "device_id": "device-a",
        "viewed_at": AWARE,
        "duration_seconds": 47,
    }
    base.update(overrides)
    return base


class TestHymnViewEventInput:
    def test_accepts_a_valid_event(self) -> None:
        event = HymnViewEventInput(**_payload())  # type: ignore[arg-type]
        assert event.app_version == ""
        assert event.platform == ""

    def test_rejects_unknown_keys(self) -> None:
        with pytest.raises(PydanticValidationError):
            HymnViewEventInput(**_payload(unexpected="x"))  # type: ignore[arg-type]

    def test_rejects_naive_viewed_at(self) -> None:
        with pytest.raises(PydanticValidationError) as exc:
            HymnViewEventInput(**_payload(viewed_at=datetime(2026, 8, 9, 19, 32)))  # type: ignore[arg-type]
        assert "UTC offset" in str(exc.value)

    def test_rejects_negative_duration(self) -> None:
        with pytest.raises(PydanticValidationError) as exc:
            HymnViewEventInput(**_payload(duration_seconds=-1))  # type: ignore[arg-type]
        assert "-1" in str(exc.value)

    def test_rejects_blank_device_id(self) -> None:
        with pytest.raises(PydanticValidationError):
            HymnViewEventInput(**_payload(device_id="   "))  # type: ignore[arg-type]

    def test_duration_below_threshold_is_still_valid(self) -> None:
        """The client owns min_seconds_to_count; the backend stores what it receives."""
        event = HymnViewEventInput(**_payload(duration_seconds=3))  # type: ignore[arg-type]
        assert event.duration_seconds == 3
