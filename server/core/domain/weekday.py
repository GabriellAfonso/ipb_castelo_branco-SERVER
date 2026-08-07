"""The single conversion between the stored weekday convention and Python's.

Two conventions are in play and their value ranges overlap, which makes mixing them
a silent bug rather than a crash:

- **stored**: ``1 = Sunday … 7 = Saturday`` — what the database holds, matching
  Django's ``__week_day`` lookup. This is the project's convention.
- **Python**: ``0 = Monday … 6 = Sunday`` — what ``datetime.weekday()`` returns.

A stored ``3`` means Tuesday; a Python ``3`` means Thursday. Nothing about the number
says which it is, so every translation must go through this module and nowhere else.
"""

STORED_SUNDAY = 1
STORED_SATURDAY = 7


def to_python_weekday(stored: int) -> int:
    """Convert a stored weekday to Python's ``datetime.weekday()`` numbering.

    >>> to_python_weekday(1)   # Sunday
    6
    >>> to_python_weekday(3)   # Tuesday
    1
    """
    return (stored + 5) % 7


def from_python_weekday(python_weekday: int) -> int:
    """Convert a Python ``datetime.weekday()`` value to the stored numbering.

    >>> from_python_weekday(6)   # Sunday
    1
    >>> from_python_weekday(1)   # Tuesday
    3
    """
    return (python_weekday + 1) % 7 + 1
