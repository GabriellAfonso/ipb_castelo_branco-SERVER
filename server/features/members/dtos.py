from pydantic import BaseModel


class BirthdayDTO(BaseModel):
    name: str
    birth_day: int
