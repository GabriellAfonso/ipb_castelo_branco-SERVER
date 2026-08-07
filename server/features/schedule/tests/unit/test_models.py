import pytest
from datetime import date, time

from django.db.models import ProtectedError

from features.members.models.member import Member
from core.models import ChurchService
from features.schedule.models.schedule import (
    MemberScheduleConfig,
    MonthlySchedule,
)


@pytest.mark.django_db
class TestChurchServiceStr:
    def test_returns_name_and_id(self) -> None:
        st = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(9, 0), end_time=time(11, 0)
        )
        assert str(st) == f"Culto - {st.id}"


@pytest.mark.django_db
class TestMemberScheduleConfigStr:
    def test_returns_member_and_schedule_type(self) -> None:
        m = Member.objects.create(name="Alice")
        st = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(9, 0), end_time=time(11, 0)
        )
        cfg = MemberScheduleConfig.objects.create(member=m, schedule_type=st)
        assert str(cfg) == "Alice - Culto"


@pytest.mark.django_db
class TestMonthlyScheduleStr:
    def test_returns_member_date_and_type(self) -> None:
        m = Member.objects.create(name="Bob")
        st = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(9, 0), end_time=time(11, 0)
        )
        ms = MonthlySchedule.objects.create(date=date(2026, 5, 3), schedule_type=st, member=m)
        assert str(ms) == "Bob - 03/05/2026 - Culto"


@pytest.mark.django_db
class TestServiceDeletionIsProtected:
    """Regression: deleting a service used to CASCADE and erase months of rota history.

    Once the service catalogue is shared (feature 007), that deletion is reachable from an
    admin endpoint, so the failure has to be loud. See research.md R-01.
    """

    def test_deleting_a_service_with_rota_rows_is_refused(self) -> None:
        member = Member.objects.create(name="Alice")
        service = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(19, 30), end_time=time(21, 30)
        )
        MonthlySchedule.objects.create(date=date(2026, 5, 3), schedule_type=service, member=member)

        with pytest.raises(ProtectedError):
            service.delete()

        assert MonthlySchedule.objects.count() == 1
        assert ChurchService.objects.filter(id=service.id).exists()

    def test_deleting_a_service_with_member_configs_is_refused(self) -> None:
        member = Member.objects.create(name="Bob")
        service = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(19, 30), end_time=time(21, 30)
        )
        MemberScheduleConfig.objects.create(member=member, schedule_type=service)

        with pytest.raises(ProtectedError):
            service.delete()

        assert MemberScheduleConfig.objects.count() == 1

    def test_an_unreferenced_service_can_still_be_deleted(self) -> None:
        service = ChurchService.objects.create(
            name="Temporário", weekday=1, start_time=time(19, 30), end_time=time(21, 30)
        )

        service.delete()

        assert not ChurchService.objects.filter(id=service.id).exists()


@pytest.mark.django_db
class TestMonthlyScheduleSave:
    def test_save_sets_year_and_month_from_date(self) -> None:
        m = Member.objects.create(name="Carol")
        st = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(9, 0), end_time=time(11, 0)
        )
        ms = MonthlySchedule(date=date(2026, 7, 12), schedule_type=st, member=m)
        ms.save()

        assert ms.year == 2026
        assert ms.month == 7

    def test_save_updates_year_month_on_date_change(self) -> None:
        m = Member.objects.create(name="Dave")
        st = ChurchService.objects.create(
            name="Culto", weekday=1, start_time=time(9, 0), end_time=time(11, 0)
        )
        ms = MonthlySchedule.objects.create(date=date(2026, 5, 3), schedule_type=st, member=m)
        assert ms.month == 5

        ms.date = date(2026, 8, 10)
        ms.save()
        ms.refresh_from_db()

        assert ms.year == 2026
        assert ms.month == 8
