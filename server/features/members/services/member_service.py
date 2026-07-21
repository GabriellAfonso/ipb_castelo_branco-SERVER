from features.members.dtos import BirthdayDTO, MemberDTO
from features.members.repositories.interfaces import MemberRepository


class MemberService:
    def __init__(self, repository: MemberRepository) -> None:
        self._repository = repository

    def list_active_members(self) -> list[MemberDTO]:
        """Return all active members.

        >>> service.list_active_members()
        [MemberDTO(id=1, name='Alice'), ...]
        """
        return self._repository.list_active_members()

    def list_birthdays_by_month_range(self, start_month: int, end_month: int) -> list[BirthdayDTO]:
        """Return members with birthdays in the given month range.

        >>> service.list_birthdays_by_month_range(1, 6)
        [BirthdayDTO(name='Alice', birth_month=1, birth_day=5), ...]
        """
        return self._repository.list_birthdays_by_month_range(start_month, end_month)
