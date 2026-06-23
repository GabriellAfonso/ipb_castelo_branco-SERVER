from typing import Protocol

from features.members.dtos import BirthdayDTO, MemberDTO


class MemberRepository(Protocol):
    """Contract for member persistence operations."""

    def list_active_members(self) -> list[MemberDTO]: ...

    def list_birthdays_by_month(self, month: int) -> list[BirthdayDTO]: ...
