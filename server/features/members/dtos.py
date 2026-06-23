from pydantic import BaseModel


class MemberDTO(BaseModel):
    id: int
    name: str


class BirthdayDTO(BaseModel):
    name: str
    gender: str | None
    birth_day: int
