"""Every error leaves the API in the canonical shape, subclasses included."""

import pytest
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
)

from core.http.exceptions import _flatten_detail, _match_by_type, _DRF_ERROR_CODE_MAP


class _LibraryTokenError(AuthenticationFailed):
    """Stands in for SimpleJWT's InvalidToken: a subclass raised from a third party."""


class TestMatchByType:
    @pytest.mark.parametrize(
        ("exc", "expected"),
        [
            (NotAuthenticated(), "NOT_AUTHENTICATED"),
            (AuthenticationFailed(), "AUTHENTICATION_FAILED"),
            (PermissionDenied(), "PERMISSION_DENIED"),
            (Throttled(), "THROTTLED"),
        ],
    )
    def test_matches_the_exact_classes(self, exc: Exception, expected: str) -> None:
        assert _match_by_type(exc, _DRF_ERROR_CODE_MAP) == expected

    def test_matches_a_subclass_raised_by_a_library(self) -> None:
        """Regression: matching on type(exc) answered UNKNOWN for SimpleJWT's InvalidToken,
        so a dead token reached the app as an unrecognised error code."""
        assert _match_by_type(_LibraryTokenError(), _DRF_ERROR_CODE_MAP) == (
            "AUTHENTICATION_FAILED"
        )

    def test_not_authenticated_wins_over_its_parent(self) -> None:
        """NotAuthenticated subclasses AuthenticationFailed, so ordering decides. Pinned
        here: reordering the map would silently relabel every anonymous request."""
        assert _match_by_type(NotAuthenticated(), _DRF_ERROR_CODE_MAP) == "NOT_AUTHENTICATED"

    def test_returns_none_for_an_unmapped_exception(self) -> None:
        assert _match_by_type(ValueError("x"), _DRF_ERROR_CODE_MAP) is None


class TestFlattenDetail:
    def test_passes_a_string_through(self) -> None:
        assert _flatten_detail("Token inválido.") == "Token inválido."

    def test_unwraps_the_simplejwt_shape(self) -> None:
        """Regression: the nested object was copied into `detail`, and a client reading it
        as text rendered raw JSON on screen."""
        wrapped = {"detail": "The user's password has been changed.", "code": "password_changed"}

        assert _flatten_detail(wrapped) == "The user's password has been changed."

    def test_falls_back_to_the_whole_mapping_when_there_is_no_inner_detail(self) -> None:
        assert "code" in _flatten_detail({"code": "something"})

    def test_always_returns_a_string(self) -> None:
        for value in ["a", {"detail": "b"}, {"code": "c"}, 42, None]:
            assert isinstance(_flatten_detail(value), str)
