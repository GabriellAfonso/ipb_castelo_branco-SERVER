"""The shared catalogue is the church's real schedule, and the hymnal groups by it.

A regression test against anyone silently changing a time, a weekday or the
takes_rota flag. The rows come from `core.0003_backfill_catalogue`.

Weekday convention: 1 = Sunday ... 7 = Saturday. Sunday is 1.
"""

from datetime import datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from conftest import make_admin_client
from core.models import ChurchService
from features.songs.models.hymnal import Hymn
from features.songs.models.hymnal_history import HymnalHistorySettings, HymnalViewEvent

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
OCCURRENCES_URL = "/api/hymnal-history/occurrences/"

SUNDAY = 1
TUESDAY = 3
THURSDAY = 5

# name, weekday, start, end, takes_rota
EXPECTED = [
    ("Terça de Oração", TUESDAY, time(19, 30), time(20, 30), True),
    ("Quinta de Oração", THURSDAY, time(19, 30), time(20, 30), True),
    ("Domingo Liturgia de Adoração", SUNDAY, time(19, 30), time(21, 0), True),
    ("Escola Bíblica Dominical", SUNDAY, time(9, 0), time(10, 0), False),
]


@pytest.mark.django_db
class TestSeededCatalogue:
    def test_all_four_services_exist(self) -> None:
        assert ChurchService.objects.count() == 4

    @pytest.mark.parametrize("name,weekday,start,end,takes_rota", EXPECTED)
    def test_service_matches_the_church_schedule(
        self, name: str, weekday: int, start: time, end: time, takes_rota: bool
    ) -> None:
        service = ChurchService.objects.get(name=name)
        assert service.weekday == weekday
        assert service.start_time == start
        assert service.end_time == end
        assert service.active is True
        assert service.takes_rota is takes_rota

    def test_sunday_school_is_held_but_takes_no_rota(self) -> None:
        """The distinction that made FR-020 necessary: active and takes_rota differ."""
        ebd = ChurchService.objects.get(name="Escola Bíblica Dominical")
        assert ebd.active is True
        assert ebd.takes_rota is False

    def test_sunday_services_do_not_overlap_even_with_grace(self) -> None:
        """EBD ends 10:00 (+30 grace = 10:30), well before the evening service."""
        ebd = ChurchService.objects.get(name="Escola Bíblica Dominical")
        evening = ChurchService.objects.get(name="Domingo Liturgia de Adoração")
        grace = HymnalHistorySettings().window_grace_minutes

        ebd_end = ebd.end_time.hour * 60 + ebd.end_time.minute + grace
        evening_start = evening.start_time.hour * 60 + evening.start_time.minute
        assert ebd_end < evening_start

    def test_prayer_meetings_share_a_time_but_not_a_weekday(self) -> None:
        tuesday = ChurchService.objects.get(name="Terça de Oração")
        thursday = ChurchService.objects.get(name="Quinta de Oração")
        assert tuesday.start_time == thursday.start_time
        assert tuesday.weekday != thursday.weekday


@pytest.mark.django_db
class TestSharedCatalogueGroupsRealViews:
    """End-to-end: the shared catalogue, the weekday conversion and the grace period."""

    def setup_method(self) -> None:
        self.client, _ = make_admin_client()
        self.hymn = Hymn.objects.create(number="50", title="Hino 50", lyrics=[])

    def _store(self, moment: datetime, device_id: str) -> None:
        HymnalViewEvent.objects.create(
            client_event_id=uuid4(),
            hymn=self.hymn,
            device_id=device_id,
            viewed_at=moment,
            duration_seconds=40,
        )

    def _occurrences(self) -> list[dict[str, object]]:
        resp = self.client.get(f"{OCCURRENCES_URL}?from=2026-08-01&to=2026-08-31")
        assert resp.status_code == 200
        return list(resp.data["occurrences"])

    def test_sunday_evening_lands_in_the_evening_service(self) -> None:
        self._store(datetime(2026, 8, 9, 19, 45, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_name"] == "Domingo Liturgia de Adoração"

    def test_sunday_morning_lands_in_sunday_school(self) -> None:
        self._store(datetime(2026, 8, 9, 9, 30, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_name"] == "Escola Bíblica Dominical"

    def test_both_sunday_services_are_two_occurrences(self) -> None:
        self._store(datetime(2026, 8, 9, 9, 30, tzinfo=SAO_PAULO), "dev-a")
        self._store(datetime(2026, 8, 9, 19, 45, tzinfo=SAO_PAULO), "dev-a")
        names = [o["service_window_name"] for o in self._occurrences()]
        assert names == ["Escola Bíblica Dominical", "Domingo Liturgia de Adoração"]

    def test_hymn_sung_after_the_scheduled_end_still_counts(self) -> None:
        """The evening service ends 21:00; a hymn at 21:20 is still that service."""
        self._store(datetime(2026, 8, 9, 21, 20, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_name"] == "Domingo Liturgia de Adoração"

    def test_well_past_the_grace_period_falls_back_to_the_day(self) -> None:
        self._store(datetime(2026, 8, 9, 22, 30, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_name"] is None

    def test_tuesday_and_thursday_prayer_meetings_are_distinct(self) -> None:
        self._store(datetime(2026, 8, 11, 19, 45, tzinfo=SAO_PAULO), "dev-a")  # terça
        self._store(datetime(2026, 8, 13, 19, 45, tzinfo=SAO_PAULO), "dev-a")  # quinta
        names = [o["service_window_name"] for o in self._occurrences()]
        assert names == ["Terça de Oração", "Quinta de Oração"]

    def test_weekday_afternoon_matches_no_service(self) -> None:
        self._store(datetime(2026, 8, 12, 15, 0, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_id"] is None
