from typing import Protocol

from features.members.dtos import BirthdayDTO


class MemberRepository(Protocol):
    """Contract for member persistence operations."""

    def list_birthdays_by_month(self, month: int) -> list[BirthdayDTO]: ...
