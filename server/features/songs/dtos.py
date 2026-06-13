from core.application.dtos.strict_base import StrictBaseModel


class PlayInput(StrictBaseModel):
    """Single play entry for registering Sunday plays."""

    song_id: int
    position: int
    tone: str = ""
