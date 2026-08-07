"""How hymn numbers sort.

Hymn numbers are strings, not integers, because the hymnal has entries like
``110-A`` sitting between ``110`` and ``111``. Sorting them as text puts ``10``
before ``2``, so they need a numeric-prefix key.

Lives in its own module because both the hymnal listing (a repository) and the
hymn ranking (a service) need it, and a repository must not import from a service.
"""


def hymn_sort_key(number: str) -> tuple[int, str]:
    """Sort hymn numbers numerically, tolerating alphanumeric suffixes like '110-A'.

    A number with no leading digits sorts first, since there is nothing to compare
    numerically. The hymnal has no such entries — all 406 start with a digit.

    >>> sorted(["110-A", "9", "110"], key=hymn_sort_key)
    ['9', '110', '110-A']
    """
    digits = ""
    for char in number:
        if not char.isdigit():
            break
        digits += char
    return (int(digits) if digits else 0, number)
