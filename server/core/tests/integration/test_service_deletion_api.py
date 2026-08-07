"""Deleting a church service must never destroy rota history.

This lives in `core` because it spans both features that share the catalogue —
neither `songs` nor `schedule` may import the other, but the guarantee is exactly
about what happens between them.

The hazard this closes: the catalogue is administered through the hymnal's
service-window endpoints, and `MonthlySchedule.schedule_type` used to CASCADE. An
admin deleting what looks like a hymnal display setting would have silently erased
every rota row for that service. See specs/007-unify-service-catalogue/research.md R-01.
"""

from datetime import date, time

import pytest

from conftest import make_admin_client
from core.models import ChurchService
from features.members.models.member import Member
from features.schedule.models.schedule import MemberScheduleConfig, MonthlySchedule

WINDOWS_URL = "/api/hymnal-history/service-windows/"


def _service(name: str = "Culto") -> ChurchService:
    return ChurchService.objects.create(
        name=name, weekday=1, start_time=time(19, 30), end_time=time(21, 0)
    )


@pytest.mark.django_db
class TestDeletingAServiceInUse:
    def test_a_service_with_rota_history_cannot_be_deleted(self) -> None:
        client, _ = make_admin_client()
        service = _service()
        member = Member.objects.create(name="Alice")
        for day in (2, 9, 16):
            MonthlySchedule.objects.create(
                date=date(2026, 8, day), schedule_type=service, member=member
            )

        resp = client.delete(f"{WINDOWS_URL}{service.id}/")

        assert resp.status_code == 409
        assert resp.data["error_code"] == "CONFLICT"
        assert "Culto" in resp.data["detail"]
        assert resp.data["rota_entries"] == 3
        assert MonthlySchedule.objects.count() == 3
        assert ChurchService.objects.filter(id=service.id).exists()

    def test_the_error_names_the_service_and_points_at_deactivating(self) -> None:
        client, _ = make_admin_client()
        service = _service("Domingo Liturgia de Adoração")
        member = Member.objects.create(name="Bob")
        MonthlySchedule.objects.create(date=date(2026, 8, 2), schedule_type=service, member=member)

        resp = client.delete(f"{WINDOWS_URL}{service.id}/")

        assert "Domingo Liturgia de Adoração" in resp.data["detail"]
        assert "Deactivate" in resp.data["detail"]
        assert resp.data["service_id"] == service.id

    def test_a_service_with_member_configs_cannot_be_deleted(self) -> None:
        client, _ = make_admin_client()
        service = _service()
        MemberScheduleConfig.objects.create(
            member=Member.objects.create(name="Carol"), schedule_type=service
        )

        resp = client.delete(f"{WINDOWS_URL}{service.id}/")

        assert resp.status_code == 409
        assert MemberScheduleConfig.objects.count() == 1

    def test_an_unreferenced_service_can_still_be_deleted(self) -> None:
        client, _ = make_admin_client()
        service = _service("Temporário")

        resp = client.delete(f"{WINDOWS_URL}{service.id}/")

        assert resp.status_code == 204
        assert not ChurchService.objects.filter(id=service.id).exists()

    def test_deactivating_is_the_supported_alternative(self) -> None:
        client, _ = make_admin_client()
        service = _service()
        member = Member.objects.create(name="Dave")
        MonthlySchedule.objects.create(date=date(2026, 8, 2), schedule_type=service, member=member)

        resp = client.patch(f"{WINDOWS_URL}{service.id}/", {"active": False}, format="json")

        assert resp.status_code == 200
        assert resp.data["active"] is False
        assert MonthlySchedule.objects.count() == 1
