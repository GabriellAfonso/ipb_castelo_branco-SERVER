"""Username normalisation, shared by every layer that keys anything on a username.

Kept separate from ``features.accounts.validators``, which owns the *character-set* rule:
``core`` may not import from ``features``, and the lockout in ``core.http.lockout`` needs
the same normalisation the DTOs apply.
"""


def normalize_username(value: str) -> str:
    """Return the canonical form of a username: trimmed and lowercased.

    Every place that stores, looks up or counts attempts against a username must agree on
    this, or the same person ends up under several keys.

    >>> normalize_username("  Ana.Paula ")
    'ana.paula'
    """
    return value.strip().lower()
