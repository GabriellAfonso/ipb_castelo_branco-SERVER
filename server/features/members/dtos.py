from pydantic import BaseModel


class BirthdayDTO(BaseModel):
    name: str
    gender: str | None
    birth_day: int
