from datetime import date, time

from pydantic import BaseModel


class ScheduleTypeDTO(BaseModel):
    id: int
    name: str
    weekday: int
    time: time


class MemberConfigDTO(BaseModel):
    member_id: int
    member_name: str
    weight: int


class MonthlyScheduleDTO(BaseModel):
    date: date
    member_id: int
    member_name: str
    schedule_type_id: int
    schedule_type_name: str
    schedule_type_time: time
