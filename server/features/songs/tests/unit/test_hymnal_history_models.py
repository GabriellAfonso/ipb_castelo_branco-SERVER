from datetime import datetime, timezone as dt_timezone

import pytest
from django.db import IntegrityError, transaction

from features.songs.models.hymnal import Hymn
from features.songs.models.hymnal_history import (
    HymnalHistorySettings,
    HymnalViewEvent,
)


@pytest.mark.django_db
class TestHymnalViewEventModel:
    def test_str_shows_hymn_number_and_moment(self) -> None:
        hymn = Hymn.objects.create(number="50", title="Grandioso És Tu", lyrics=[])
        event = HymnalViewEvent.objects.create(
            client_event_id="5b1f9a4e-1c2d-4f3a-9b8c-7d6e5f4a3b2c",
            hymn=hymn,
            device_id="device-a",
            viewed_at=datetime(2026, 8, 9, 22, 32, tzinfo=dt_timezone.utc),
            duration_seconds=47,
        )
        assert "50" in str(event)
        assert "2026-08-09" in str(event)

    def test_client_event_id_is_unique(self) -> None:
        hymn = Hymn.objects.create(number="1", title="First", lyrics=[])
        shared_id = "11111111-1111-4111-8111-111111111111"
        HymnalViewEvent.objects.create(
            client_event_id=shared_id,
            hymn=hymn,
            device_id="device-a",
            viewed_at=datetime(2026, 8, 9, 22, 0, tzinfo=dt_timezone.utc),
            duration_seconds=40,
        )
        with pytest.raises(IntegrityError):
            HymnalViewEvent.objects.create(
                client_event_id=shared_id,
                hymn=hymn,
                device_id="device-b",
                viewed_at=datetime(2026, 8, 9, 23, 0, tzinfo=dt_timezone.utc),
                duration_seconds=40,
            )


@pytest.mark.django_db
class TestHymnalHistorySettingsModel:
    def test_defaults(self) -> None:
        row = HymnalHistorySettings.objects.create(id=1)
        assert row.min_seconds_to_count == 30
        assert row.collapse_window_minutes == 10
        assert row.max_batch_size == 200
        assert row.max_past_days == 90
        assert row.future_tolerance_minutes == 5

    def test_second_row_is_rejected(self) -> None:
        HymnalHistorySettings.objects.create(id=1)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                HymnalHistorySettings.objects.create(id=2)

    def test_str(self) -> None:
        assert str(HymnalHistorySettings(id=1)) == "Hymnal history settings"
