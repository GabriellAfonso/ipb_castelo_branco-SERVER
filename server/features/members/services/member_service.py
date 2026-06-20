from features.members.dtos import BirthdayDTO
from features.members.repositories.interfaces import MemberRepository


class MemberService:
    def __init__(self, repository: MemberRepository) -> None:
        self._repository = repository

    def list_birthdays_by_month(self, month: int) -> list[BirthdayDTO]:
        """Return members with birthdays in the given month.

        >>> service.list_birthdays_by_month(7)
        [BirthdayDTO(name='Alice', birth_day=5), ...]
        """
        return self._repository.list_birthdays_by_month(month)
