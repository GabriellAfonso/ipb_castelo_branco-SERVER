from django.db.models.functions import ExtractDay, ExtractMonth

from features.members.dtos import BirthdayDTO, MemberDTO
from features.members.models.member import Member


class DjangoMemberRepository:
    """Member repository using Django ORM."""

    def list_active_members(self) -> list[MemberDTO]:
        """Return all active members ordered by name.

        >>> repo.list_active_members()
        [MemberDTO(id=1, name='Alice'), ...]
        """
        qs = Member.objects.filter(is_active=True).order_by("name").values_list("id", "name")
        return [MemberDTO(id=pk, name=name) for pk, name in qs]

    def list_birthdays_by_month_range(self, start_month: int, end_month: int) -> list[BirthdayDTO]:
        """Return active members born in the given month range, ordered by month then day.

        >>> repo.list_birthdays_by_month_range(1, 6)
        [BirthdayDTO(name='Alice', gender='F', birth_month=1, birth_day=5), ...]
        """
        qs = (
            Member.objects.filter(
                birth_date__month__gte=start_month,
                birth_date__month__lte=end_month,
                is_active=True,
            )
            .exclude(birth_date__isnull=True)
            .annotate(month=ExtractMonth("birth_date"), day=ExtractDay("birth_date"))
            .order_by("month", "day")
            .values_list("name", "gender", "month", "day")
        )
        return [
            BirthdayDTO(name=name, gender=gender, birth_month=month, birth_day=day)
            for name, gender, month, day in qs
        ]
