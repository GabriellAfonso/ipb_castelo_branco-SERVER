from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_auth_client, make_member_client, make_user
from features.members.models.member import Member


ENDPOINT = "/api/members/birthdays/"


@pytest.mark.django_db
class TestMemberBirthdaysAPIView:
    # --- US1: View birthdays by month ---

    def test_member_returns_birthdays_for_month(self) -> None:
        Member.objects.create(name="Alice", birth_date=date(1990, 7, 5), is_active=True)
        Member.objects.create(name="Bob", birth_date=date(1985, 7, 23), is_active=True)
        Member.objects.create(name="Carol", birth_date=date(1992, 8, 10), is_active=True)
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": 7})

        assert resp.status_code == 200
        birthdays = resp.data["birthdays"]
        assert len(birthdays) == 2
        assert birthdays[0]["name"] == "Alice"
        assert birthdays[0]["birth_day"] == 5
        assert birthdays[1]["name"] == "Bob"
        assert birthdays[1]["birth_day"] == 23

    def test_empty_month_returns_empty_list(self) -> None:
        Member.objects.create(name="Alice", birth_date=date(1990, 7, 5), is_active=True)
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": 2})

        assert resp.status_code == 200
        assert resp.data["birthdays"] == []

    def test_excludes_null_birth_date(self) -> None:
        Member.objects.create(name="Alice", birth_date=date(1990, 7, 5), is_active=True)
        Member.objects.create(name="NoBirthday", birth_date=None, is_active=True)
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": 7})

        names = [b["name"] for b in resp.data["birthdays"]]
        assert "Alice" in names
        assert "NoBirthday" not in names

    def test_excludes_inactive_members(self) -> None:
        Member.objects.create(name="Active", birth_date=date(1990, 7, 5), is_active=True)
        Member.objects.create(name="Inactive", birth_date=date(1990, 7, 10), is_active=False)
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": 7})

        names = [b["name"] for b in resp.data["birthdays"]]
        assert "Active" in names
        assert "Inactive" not in names

    def test_orders_by_day_ascending(self) -> None:
        Member.objects.create(name="Late", birth_date=date(1990, 3, 28), is_active=True)
        Member.objects.create(name="Early", birth_date=date(1995, 3, 3), is_active=True)
        Member.objects.create(name="Mid", birth_date=date(1988, 3, 15), is_active=True)
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": 3})

        days = [b["birth_day"] for b in resp.data["birthdays"]]
        assert days == [3, 15, 28]

    # --- US2: Invalid month handling ---

    def test_missing_month_returns_400(self) -> None:
        client, _ = make_member_client()

        resp = client.get(ENDPOINT)

        assert resp.status_code == 400
        assert "month" in resp.data

    def test_invalid_month_zero_returns_400(self) -> None:
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": 0})

        assert resp.status_code == 400

    def test_invalid_month_thirteen_returns_400(self) -> None:
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": 13})

        assert resp.status_code == 400

    def test_invalid_month_negative_returns_400(self) -> None:
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": -1})

        assert resp.status_code == 400

    def test_invalid_month_non_numeric_returns_400(self) -> None:
        client, _ = make_member_client()

        resp = client.get(ENDPOINT, {"month": "abc"})

        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self) -> None:
        resp = APIClient().get(ENDPOINT, {"month": 7})

        assert resp.status_code == 401

    def test_non_member_returns_403(self) -> None:
        user = make_user(username="regular")
        client = make_auth_client(user)

        resp = client.get(ENDPOINT, {"month": 7})

        assert resp.status_code == 403
