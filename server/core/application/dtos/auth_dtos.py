from core.application.dtos.strict_base import StrictBaseModel
from core.application.username import normalize_username
from typing import Optional

from pydantic import Field, field_validator


class RegisterDTO(StrictBaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, v: str) -> str:
        return normalize_username(v)


class LoginDTO(StrictBaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1)

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, v: str) -> str:
        return normalize_username(v)


class TokenDTO(StrictBaseModel):
    access: str
    refresh: Optional[str] = None
