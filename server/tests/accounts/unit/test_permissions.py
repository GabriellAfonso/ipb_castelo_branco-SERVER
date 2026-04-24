from unittest.mock import MagicMock

from features.core.http.permissions import IsAdminUser, IsMemberUser


def _make_request(user: object | None = None) -> MagicMock:
    request = MagicMock()
    request.user = user
    return request


def _make_user(is_authenticated: bool = True) -> MagicMock:
    user = MagicMock()
    user.is_authenticated = is_authenticated
    user.profile = MagicMock(is_member=False, is_admin=False)
    return user


# ---------------------------------------------------------------------------
# IsMemberUser
# ---------------------------------------------------------------------------


class TestIsMemberUser:
    perm = IsMemberUser()

    def test_member_allowed(self) -> None:
        user = _make_user()
        user.profile.is_member = True
        assert self.perm.has_permission(_make_request(user), MagicMock()) is True

    def test_non_member_denied(self) -> None:
        user = _make_user()
        user.profile.is_member = False
        assert self.perm.has_permission(_make_request(user), MagicMock()) is False

    def test_unauthenticated_denied(self) -> None:
        user = _make_user(is_authenticated=False)
        assert self.perm.has_permission(_make_request(user), MagicMock()) is False


# ---------------------------------------------------------------------------
# IsAdminUser
# ---------------------------------------------------------------------------


class TestIsAdminUser:
    perm = IsAdminUser()

    def test_admin_allowed(self) -> None:
        user = _make_user()
        user.profile.is_admin = True
        assert self.perm.has_permission(_make_request(user), MagicMock()) is True

    def test_non_admin_denied(self) -> None:
        user = _make_user()
        user.profile.is_admin = False
        assert self.perm.has_permission(_make_request(user), MagicMock()) is False

    def test_unauthenticated_denied(self) -> None:
        user = _make_user(is_authenticated=False)
        assert self.perm.has_permission(_make_request(user), MagicMock()) is False
