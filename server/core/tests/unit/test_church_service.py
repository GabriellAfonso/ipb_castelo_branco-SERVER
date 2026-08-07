from datetime import time

import pytest
from django.db import IntegrityError, transaction

from core.models import ChurchService


@pytest.mark.django_db
class TestChurchServiceConstraints:
    def test_end_time_must_be_after_start_time(self) -> None:
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ChurchService.objects.create(
                    name="Inválido", weekday=1, start_time=time(21, 0), end_time=time(19, 0)
                )

    def test_end_time_equal_to_start_time_is_rejected(self) -> None:
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ChurchService.objects.create(
                    name="Inválido", weekday=1, start_time=time(19, 0), end_time=time(19, 0)
                )

    @pytest.mark.parametrize("weekday", [0, 8, 99])
    def test_weekday_outside_one_to_seven_is_rejected(self, weekday: int) -> None:
        """Sunday is 1 and Saturday is 7 — 0 is not a valid weekday here."""
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ChurchService.objects.create(
                    name="Inválido",
                    weekday=weekday,
                    start_time=time(19, 0),
                    end_time=time(21, 0),
                )

    @pytest.mark.parametrize("weekday", [1, 4, 7])
    def test_every_valid_weekday_is_accepted(self, weekday: int) -> None:
        service = ChurchService.objects.create(
            name=f"Culto {weekday}", weekday=weekday, start_time=time(19, 0), end_time=time(21, 0)
        )
        assert service.weekday == weekday


@pytest.mark.django_db
class TestChurchServiceFlags:
    def test_defaults_are_active_and_rostered(self) -> None:
        service = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(19, 0), end_time=time(21, 0)
        )
        assert service.active is True
        assert service.takes_rota is True

    def test_active_and_takes_rota_are_independent(self) -> None:
        """Escola Bíblica Dominical is held every Sunday and takes no rota."""
        service = ChurchService.objects.create(
            name="Escola Bíblica Dominical",
            weekday=1,
            start_time=time(9, 0),
            end_time=time(10, 0),
            active=True,
            takes_rota=False,
        )
        assert service.active is True
        assert service.takes_rota is False


@pytest.mark.django_db
class TestChurchServiceMeta:
    def test_str_matches_the_previous_model(self) -> None:
        """The rota response groups by name; __str__ is unchanged from ScheduleType."""
        service = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(19, 0), end_time=time(21, 0)
        )
        assert str(service) == f"Culto - {service.id}"

    def test_ordering_is_weekday_then_start_time(self) -> None:
        # Migration 0003 seeds the church's real services; assert on a controlled set.
        ChurchService.objects.all().delete()
        ChurchService.objects.create(
            name="Domingo Noite", weekday=1, start_time=time(19, 30), end_time=time(21, 0)
        )
        ChurchService.objects.create(
            name="EBD", weekday=1, start_time=time(9, 0), end_time=time(10, 0)
        )
        ChurchService.objects.create(
            name="Terça", weekday=3, start_time=time(19, 30), end_time=time(20, 30)
        )
        assert [s.name for s in ChurchService.objects.all()] == ["EBD", "Domingo Noite", "Terça"]
