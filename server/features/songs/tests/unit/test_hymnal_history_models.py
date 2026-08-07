from datetime import datetime, time, timezone as dt_timezone

import pytest
from django.db import IntegrityError, transaction

from features.songs.models.hymnal import Hymn
from features.songs.models.hymnal_history import (
    HymnalHistorySettings,
    HymnalViewEvent,
    ServiceWindow,
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


@pytest.fixture(autouse=True)
def _isolate_from_seeded_windows(db: None) -> None:
    """Migration 0006 seeds the church's real windows. These tests assert on a
    controlled set, so they start from an empty table."""
    ServiceWindow.objects.all().delete()


@pytest.mark.django_db
class TestServiceWindowModel:
    def test_str_includes_name_and_range(self) -> None:
        window = ServiceWindow.objects.create(
            name="Culto de Domingo à Noite",
            weekday=6,
            start_time=time(19, 0),
            end_time=time(21, 0),
        )
        assert "Culto de Domingo à Noite" in str(window)

    def test_end_time_must_be_after_start_time(self) -> None:
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ServiceWindow.objects.create(
                    name="Inválido",
                    weekday=6,
                    start_time=time(21, 0),
                    end_time=time(19, 0),
                )

    def test_end_time_equal_to_start_time_is_rejected(self) -> None:
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ServiceWindow.objects.create(
                    name="Inválido",
                    weekday=6,
                    start_time=time(19, 0),
                    end_time=time(19, 0),
                )

    def test_weekday_above_six_is_rejected(self) -> None:
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ServiceWindow.objects.create(
                    name="Inválido",
                    weekday=7,
                    start_time=time(19, 0),
                    end_time=time(21, 0),
                )

    def test_ordering_is_weekday_then_start_time(self) -> None:
        ServiceWindow.objects.create(
            name="Noite", weekday=6, start_time=time(19, 0), end_time=time(21, 0)
        )
        ServiceWindow.objects.create(
            name="Manhã", weekday=6, start_time=time(9, 0), end_time=time(10, 30)
        )
        ServiceWindow.objects.create(
            name="Quarta", weekday=2, start_time=time(19, 30), end_time=time(21, 0)
        )
        names = [w.name for w in ServiceWindow.objects.all()]
        assert names == ["Quarta", "Manhã", "Noite"]


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
