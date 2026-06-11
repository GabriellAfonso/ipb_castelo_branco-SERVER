from typing import Optional

from core.application.dtos.strict_base import StrictBaseModel


class GoogleUserDTO(StrictBaseModel):
    email: str
    first_name: str = ""
    last_name: str = ""
    picture_url: Optional[str] = None
    email_verified: bool = False
