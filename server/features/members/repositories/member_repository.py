from django.db.models.functions import ExtractDay

from features.members.dtos import BirthdayDTO
from features.members.models.member import Member


class DjangoMemberRepository:
    """Member repository using Django ORM."""

    def list_birthdays_by_month(self, month: int) -> list[BirthdayDTO]:
        """Return active members born in the given month, ordered by day.

        >>> repo.list_birthdays_by_month(7)
        [BirthdayDTO(name='Alice', gender='F', birth_day=5), ...]
        """
        qs = (
            Member.objects.filter(birth_date__month=month, is_active=True)
            .exclude(birth_date__isnull=True)
            .annotate(day=ExtractDay("birth_date"))
            .order_by("day")
            .values_list("name", "gender", "day")
        )
        return [BirthdayDTO(name=name, gender=gender, birth_day=day) for name, gender, day in qs]
