"""Both directions of the weekday conversion, for all seven days.

The two conventions overlap numerically, so these tests pin real days to real numbers
rather than asserting the formula against itself.
"""

import pytest

from core.domain.weekday import from_python_weekday, to_python_weekday

# (stored, python, day name) — stored is 1=Sunday, python is 0=Monday
ALL_DAYS = [
    (1, 6, "Sunday"),
    (2, 0, "Monday"),
    (3, 1, "Tuesday"),
    (4, 2, "Wednesday"),
    (5, 3, "Thursday"),
    (6, 4, "Friday"),
    (7, 5, "Saturday"),
]


class TestToPythonWeekday:
    @pytest.mark.parametrize("stored,python,day", ALL_DAYS)
    def test_every_day(self, stored: int, python: int, day: str) -> None:
        assert to_python_weekday(stored) == python, day

    def test_the_three_services_in_production(self) -> None:
        """Terça=3, Quinta=5, Domingo=1 — the values actually stored."""
        assert to_python_weekday(3) == 1  # Tuesday
        assert to_python_weekday(5) == 3  # Thursday
        assert to_python_weekday(1) == 6  # Sunday


class TestFromPythonWeekday:
    @pytest.mark.parametrize("stored,python,day", ALL_DAYS)
    def test_every_day(self, stored: int, python: int, day: str) -> None:
        assert from_python_weekday(python) == stored, day


class TestRoundTrip:
    @pytest.mark.parametrize("stored,python,day", ALL_DAYS)
    def test_stored_survives_a_round_trip(self, stored: int, python: int, day: str) -> None:
        assert from_python_weekday(to_python_weekday(stored)) == stored, day

    @pytest.mark.parametrize("stored,python,day", ALL_DAYS)
    def test_python_survives_a_round_trip(self, stored: int, python: int, day: str) -> None:
        assert to_python_weekday(from_python_weekday(python)) == python, day


class TestConventionsGenuinelyDiffer:
    def test_the_same_number_means_different_days(self) -> None:
        """Why this module exists: 3 is Tuesday stored, Thursday in Python."""
        assert to_python_weekday(3) != 3
        assert from_python_weekday(3) != 3


class TestBothFeaturesAgree:
    """The whole point of this module: one stored value, one real weekday.

    The rota converts stored -> Python to pick dates; the hymnal converts
    Python -> stored to match a service. If they disagree, a service either
    generates on the wrong days or silently never matches a hymn view.
    """

    @pytest.mark.parametrize("stored,python,day", ALL_DAYS)
    def test_the_rota_and_the_hymnal_resolve_the_same_day(
        self, stored: int, python: int, day: str
    ) -> None:
        # What the rota does when picking dates for a service.
        rota_target = to_python_weekday(stored)
        # What the hymnal does when deciding which service a view belongs to.
        hymnal_lookup = from_python_weekday(rota_target)

        assert rota_target == python, day
        assert hymnal_lookup == stored, day

    def test_a_sunday_service_resolves_to_a_real_sunday(self) -> None:
        from datetime import date

        sunday_service_weekday = 1
        # 9 August 2026 is a Sunday.
        real_sunday = date(2026, 8, 9)

        assert real_sunday.weekday() == to_python_weekday(sunday_service_weekday)
        assert from_python_weekday(real_sunday.weekday()) == sunday_service_weekday
