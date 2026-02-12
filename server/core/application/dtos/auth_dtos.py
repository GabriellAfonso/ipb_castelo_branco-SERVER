from core.application.dtos.strict_base import StrictBaseModel
from pydantic import Field
from typing import Optional
from pydantic import EmailStr


class RegisterDTO(StrictBaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=8),
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)


class LoginDTO(StrictBaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1)


class TokenDTO(StrictBaseModel):
    access: str
    refresh: Optional[str] = None
