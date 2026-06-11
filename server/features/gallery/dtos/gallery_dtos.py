from core.application.dtos.strict_base import StrictBaseModel


class UploadResult(StrictBaseModel):
    """Result of a batch photo upload."""

    created_count: int = 0
    errors: list[str] = []

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
