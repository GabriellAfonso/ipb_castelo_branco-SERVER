"""Unit tests for ``core.application.username``."""

import pytest

from core.application.username import normalize_username


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ana.Paula", "ana.paula"),
        ("  admin  ", "admin"),
        ("\tADMIN\n", "admin"),
        ("already-normal", "already-normal"),
        ("", ""),
    ],
)
def test_normalize_username(raw: str, expected: str) -> None:
    assert normalize_username(raw) == expected
