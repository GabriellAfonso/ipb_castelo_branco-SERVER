"""The seeded service windows are the church's real schedule — a regression test
against anyone silently changing a time or a weekday.

Weekday convention: 0 = Monday ... 6 = Sunday. Sunday is 6.
"""

from datetime import datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from conftest import make_admin_client
from features.songs.models.hymnal import Hymn
from features.songs.models.hymnal_history import (
    HymnalHistorySettings,
    HymnalViewEvent,
    ServiceWindow,
)

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
OCCURRENCES_URL = "/api/hymnal-history/occurrences/"

EXPECTED = [
    ("Terça de Oração", 1, time(19, 30), time(20, 30)),
    ("Quinta de Oração", 3, time(19, 30), time(20, 30)),
    ("Escola Bíblica Dominical", 6, time(9, 0), time(10, 0)),
    ("Culto Dominical", 6, time(19, 30), time(21, 0)),
]


@pytest.mark.django_db
class TestSeededServiceWindows:
    def test_all_four_windows_exist(self) -> None:
        assert ServiceWindow.objects.count() == 4

    @pytest.mark.parametrize("name,weekday,start,end", EXPECTED)
    def test_window_matches_the_church_schedule(
        self, name: str, weekday: int, start: time, end: time
    ) -> None:
        window = ServiceWindow.objects.get(name=name)
        assert window.weekday == weekday
        assert window.start_time == start
        assert window.end_time == end
        assert window.active is True

    def test_sunday_windows_do_not_overlap_even_with_grace(self) -> None:
        """EBD ends 10:00 (+30 grace = 10:30), well before Culto Dominical at 19:30."""
        ebd = ServiceWindow.objects.get(name="Escola Bíblica Dominical")
        culto = ServiceWindow.objects.get(name="Culto Dominical")
        grace = HymnalHistorySettings().window_grace_minutes

        ebd_end_minutes = ebd.end_time.hour * 60 + ebd.end_time.minute + grace
        culto_start_minutes = culto.start_time.hour * 60 + culto.start_time.minute
        assert ebd_end_minutes < culto_start_minutes

    def test_prayer_meetings_share_a_time_but_not_a_weekday(self) -> None:
        tuesday = ServiceWindow.objects.get(name="Terça de Oração")
        thursday = ServiceWindow.objects.get(name="Quinta de Oração")
        assert tuesday.start_time == thursday.start_time
        assert tuesday.weekday != thursday.weekday


@pytest.mark.django_db
class TestSeededWindowsGroupRealViews:
    """End-to-end against the real schedule — the seed, the matching and the
    grace period working together."""

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

    def test_sunday_evening_lands_in_culto_dominical(self) -> None:
        self._store(datetime(2026, 8, 9, 19, 45, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_name"] == "Culto Dominical"

    def test_sunday_morning_lands_in_ebd(self) -> None:
        self._store(datetime(2026, 8, 9, 9, 30, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_name"] == "Escola Bíblica Dominical"

    def test_ebd_and_culto_on_the_same_sunday_are_two_occurrences(self) -> None:
        self._store(datetime(2026, 8, 9, 9, 30, tzinfo=SAO_PAULO), "dev-a")
        self._store(datetime(2026, 8, 9, 19, 45, tzinfo=SAO_PAULO), "dev-a")
        names = [o["service_window_name"] for o in self._occurrences()]
        assert names == ["Escola Bíblica Dominical", "Culto Dominical"]

    def test_hymn_sung_after_the_scheduled_end_still_counts(self) -> None:
        """Culto Dominical ends 21:00; a hymn at 21:20 is still that service."""
        self._store(datetime(2026, 8, 9, 21, 20, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_name"] == "Culto Dominical"

    def test_well_past_the_grace_period_falls_back_to_the_day(self) -> None:
        self._store(datetime(2026, 8, 9, 22, 30, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_name"] is None

    def test_tuesday_and_thursday_prayer_meetings_are_distinct(self) -> None:
        self._store(datetime(2026, 8, 11, 19, 45, tzinfo=SAO_PAULO), "dev-a")  # terça
        self._store(datetime(2026, 8, 13, 19, 45, tzinfo=SAO_PAULO), "dev-a")  # quinta
        names = [o["service_window_name"] for o in self._occurrences()]
        assert names == ["Terça de Oração", "Quinta de Oração"]

    def test_weekday_afternoon_matches_no_window(self) -> None:
        self._store(datetime(2026, 8, 12, 15, 0, tzinfo=SAO_PAULO), "dev-a")
        assert self._occurrences()[0]["service_window_id"] is None
