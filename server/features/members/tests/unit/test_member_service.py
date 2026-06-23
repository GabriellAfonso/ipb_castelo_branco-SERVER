from features.members.dtos import BirthdayDTO, MemberDTO
from features.members.services.member_service import MemberService


class FakeMemberRepository:
    def __init__(self, birthdays: list[BirthdayDTO]) -> None:
        self._birthdays = birthdays
        self.last_month: int | None = None

    def list_active_members(self) -> list[MemberDTO]:
        return []

    def list_birthdays_by_month(self, month: int) -> list[BirthdayDTO]:
        self.last_month = month
        return self._birthdays


class TestMemberService:
    def test_list_birthdays_by_month_delegates_to_repository(self) -> None:
        expected = [
            BirthdayDTO(name="Alice", gender="F", birth_day=5),
            BirthdayDTO(name="Bob", gender="M", birth_day=23),
        ]
        repo = FakeMemberRepository(expected)
        service = MemberService(repository=repo)

        result = service.list_birthdays_by_month(7)

        assert result == expected
        assert repo.last_month == 7

    def test_list_birthdays_by_month_returns_empty_list(self) -> None:
        repo = FakeMemberRepository([])
        service = MemberService(repository=repo)

        result = service.list_birthdays_by_month(2)

        assert result == []
        assert repo.last_month == 2
