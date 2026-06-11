from core.application.dtos.strict_base import StrictBaseModel


Verse = str | list[str]


class BibleBook(StrictBaseModel):
    """Single book of a Bible version.

    Most verses are plain strings, but some NAA entries contain
    nested lists (multiple paragraphs within a single verse number).
    """

    abbrev: str
    name: str
    chapters: list[list[Verse]]
