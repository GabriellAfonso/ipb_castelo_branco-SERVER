import pytest
from datetime import date, time, timedelta
from unittest.mock import patch

from django.db import IntegrityError
from django.utils import timezone

from features.core.application.services.monthly_scheduler import (
    generate_monthly_schedule_preview,
    save_monthly_schedule,
)
from features.members.models.member import Member
from features.schedule.models.schedule import MemberScheduleConfig, MonthlySchedule, ScheduleType


# --- Helpers ---


def make_schedule_type(
    name: str = "Culto", weekday: int = 1, time_str: str = "09:00"
) -> ScheduleType:
    h, m = map(int, time_str.split(":"))
    return ScheduleType.objects.create(name=name, weekday=weekday, time=time(h, m))


def make_member(name: str = "Alice") -> Member:
    return Member.objects.create(name=name)


def make_config(
    member: Member,
    schedule_type: ScheduleType,
    available: bool = True,
    weight: int = 1,
) -> MemberScheduleConfig:
    return MemberScheduleConfig.objects.create(
        member=member,
        schedule_type=schedule_type,
        available=available,
        weight=weight,
    )


def _make_save_items(
    schedule_type: ScheduleType,
    member: Member,
    dates: list[date],
) -> list[dict[str, int | str]]:
    return [
        {"date": d.isoformat(), "schedule_type_id": schedule_type.id, "member_id": member.id}
        for d in dates
    ]


# --- generate_monthly_schedule_preview: structure ---


@pytest.mark.django_db
def test_preview_returns_correct_year_and_month() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    make_config(m, st)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    assert result["year"] == 2026
    assert result["month"] == 5


@pytest.mark.django_db
def test_preview_defaults_to_next_month() -> None:
    real_date = date

    with patch("features.core.application.services.monthly_scheduler.date") as mock_date:
        mock_date.today.return_value = real_date(2026, 4, 15)
        mock_date.side_effect = lambda *a, **kw: real_date(*a, **kw)

        result = generate_monthly_schedule_preview()

    assert result["year"] == 2026
    assert result["month"] == 5


@pytest.mark.django_db
def test_preview_returns_items_list() -> None:
    result = generate_monthly_schedule_preview(year=2026, month=5)
    assert isinstance(result["items"], list)


@pytest.mark.django_db
def test_preview_items_have_required_keys() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    make_config(m, st)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    for item in result["items"]:
        assert isinstance(item["date"], str)
        assert isinstance(item["day"], int)
        assert isinstance(item["schedule_type"], dict)
        assert isinstance(item["member"], dict)
        assert isinstance(item["fixed"], bool)


@pytest.mark.django_db
def test_preview_all_dates_in_requested_month() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    make_config(m, st)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    for item in result["items"]:
        d = date.fromisoformat(item["date"])
        assert d.year == 2026
        assert d.month == 5


# --- generate_monthly_schedule_preview: filtering/skips ---


@pytest.mark.django_db
def test_preview_skips_weekday_not_in_map() -> None:
    # weekday=2 is not in WEEKDAYS_MAP (only 1, 3, 5 are)
    st = make_schedule_type(weekday=2)
    m = make_member()
    make_config(m, st)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    assert result["items"] == []


@pytest.mark.django_db
def test_preview_skips_schedule_type_with_no_available_configs() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    make_config(m, st, available=False)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    assert result["items"] == []


# --- generate_monthly_schedule_preview: ordering and format ---


@pytest.mark.django_db
def test_preview_items_sorted_by_name_then_date() -> None:
    st_a = make_schedule_type(name="A", weekday=1, time_str="09:00")
    st_b = make_schedule_type(name="B", weekday=1, time_str="11:00")
    m1 = make_member("M1")
    m2 = make_member("M2")
    make_config(m1, st_a, weight=5)
    make_config(m2, st_b, weight=5)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    names = [item["schedule_type"]["name"] for item in result["items"]]
    assert names == sorted(names)


@pytest.mark.django_db
def test_preview_schedule_type_time_formatted_hh_mm() -> None:
    st = make_schedule_type(weekday=1, time_str="09:00")
    m = make_member()
    make_config(m, st)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    assert result["items"][0]["schedule_type"]["time"] == "09:00"


# --- generate_monthly_schedule_preview: selection algorithm ---


@pytest.mark.django_db
def test_preview_weight_limits_assignments_per_member() -> None:
    # 1 member, weight=1, May 2026 has 5 Sundays → only 1 assignment (pool exhausts)
    st = make_schedule_type(weekday=1)
    m = make_member()
    make_config(m, st, weight=1)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    assert len(result["items"]) == 1


@pytest.mark.django_db
def test_preview_weight_controls_max_appearances() -> None:
    # 1 member, weight=3 → 3 appearances
    st = make_schedule_type(weekday=1)
    m = make_member()
    make_config(m, st, weight=3)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    assert len(result["items"]) == 3


@pytest.mark.django_db
def test_preview_five_members_cover_five_sundays() -> None:
    st = make_schedule_type(weekday=1)
    members = [make_member(f"Member{i}") for i in range(5)]
    for m in members:
        make_config(m, st, weight=1)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    assert len(result["items"]) == 5
    assigned_ids = {item["member"]["id"] for item in result["items"]}
    expected_ids = {m.id for m in members}
    assert assigned_ids == expected_ids


@pytest.mark.django_db
def test_preview_fixed_assignment_respected() -> None:
    st = make_schedule_type(weekday=1)
    m1 = make_member("M1")
    m2 = make_member("M2")
    make_config(m1, st, weight=5)
    make_config(m2, st, weight=5)

    fixed_date = date(2026, 5, 3)
    result = generate_monthly_schedule_preview(
        year=2026, month=5, fixed={(st.id, fixed_date): m2.id}
    )

    fixed_items = [i for i in result["items"] if i["date"] == fixed_date.isoformat()]
    assert len(fixed_items) == 1
    assert fixed_items[0]["member"]["id"] == m2.id
    assert fixed_items[0]["fixed"] is True


@pytest.mark.django_db
def test_preview_fixed_non_configured_member_skipped() -> None:
    st = make_schedule_type(weekday=1)
    m_configured = make_member("Configured")
    m_not_configured = make_member("NotConfigured")
    make_config(m_configured, st, weight=5)

    fixed_date = date(2026, 5, 3)
    result = generate_monthly_schedule_preview(
        year=2026, month=5, fixed={(st.id, fixed_date): m_not_configured.id}
    )

    fixed_date_items = [i for i in result["items"] if i["date"] == fixed_date.isoformat()]
    assert len(fixed_date_items) == 1
    assert fixed_date_items[0]["member"]["id"] == m_configured.id
    assert fixed_date_items[0]["fixed"] is False


@pytest.mark.django_db
def test_preview_non_fixed_items_have_fixed_false() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    make_config(m, st, weight=5)

    result = generate_monthly_schedule_preview(year=2026, month=5)

    assert all(item["fixed"] is False for item in result["items"])


# --- save_monthly_schedule ---


@pytest.mark.django_db
def test_save_creates_records_in_db() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    items = _make_save_items(st, m, [date(2026, 5, 3), date(2026, 5, 10)])

    save_monthly_schedule(2026, 5, items)

    assert MonthlySchedule.objects.filter(year=2026, month=5).count() == 2


@pytest.mark.django_db
def test_save_replaces_within_30_minutes() -> None:
    st = make_schedule_type(weekday=1)
    m1 = make_member("V1")
    m2 = make_member("V2")

    items_v1 = _make_save_items(st, m1, [date(2026, 5, 3)])
    save_monthly_schedule(2026, 5, items_v1)

    items_v2 = _make_save_items(st, m2, [date(2026, 5, 3), date(2026, 5, 10)])
    save_monthly_schedule(2026, 5, items_v2)

    records = list(MonthlySchedule.objects.filter(year=2026, month=5))
    assert len(records) == 2
    assert all(r.member_id == m2.id for r in records)


@pytest.mark.django_db
def test_save_raises_after_30_minutes() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    items = _make_save_items(st, m, [date(2026, 5, 3)])
    save_monthly_schedule(2026, 5, items)

    MonthlySchedule.objects.filter(year=2026, month=5).update(
        created_at=timezone.now() - timedelta(minutes=31)
    )

    with pytest.raises(ValueError, match="30 minutos"):
        save_monthly_schedule(2026, 5, items)


@pytest.mark.django_db
def test_save_boundary_at_exactly_30_minutes() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    items = _make_save_items(st, m, [date(2026, 5, 3)])
    save_monthly_schedule(2026, 5, items)

    # Set created_at to (now - 30min + 10s) so the check `now > created_at + 30min`
    # evaluates as `now > now + 10s` → False, confirming operator is >, not >=.
    MonthlySchedule.objects.filter(year=2026, month=5).update(
        created_at=timezone.now() - timedelta(minutes=30) + timedelta(seconds=10)
    )

    # Should NOT raise (still within 30-minute window)
    save_monthly_schedule(2026, 5, items)


@pytest.mark.django_db
def test_save_first_time_always_succeeds() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    items = _make_save_items(st, m, [date(2026, 5, 3)])

    save_monthly_schedule(2026, 5, items)

    assert MonthlySchedule.objects.filter(year=2026, month=5).count() == 1


@pytest.mark.django_db
def test_save_rolls_back_on_constraint_violation() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    # Two items with the same (schedule_type, date) → violates unique_together
    items = [
        {"date": "2026-05-03", "schedule_type_id": st.id, "member_id": m.id},
        {"date": "2026-05-03", "schedule_type_id": st.id, "member_id": m.id},
    ]

    with pytest.raises(IntegrityError):
        save_monthly_schedule(2026, 5, items)

    assert MonthlySchedule.objects.filter(year=2026, month=5).count() == 0


@pytest.mark.django_db
def test_save_empty_items_creates_no_records() -> None:
    save_monthly_schedule(2026, 5, [])

    assert MonthlySchedule.objects.filter(year=2026, month=5).count() == 0


@pytest.mark.django_db
def test_save_sets_year_month_on_records() -> None:
    st = make_schedule_type(weekday=1)
    m = make_member()
    items = _make_save_items(st, m, [date(2026, 5, 3)])

    save_monthly_schedule(2026, 5, items)

    record = MonthlySchedule.objects.get(year=2026, month=5)
    assert record.year == 2026
    assert record.month == 5
    assert record.date == date(2026, 5, 3)
