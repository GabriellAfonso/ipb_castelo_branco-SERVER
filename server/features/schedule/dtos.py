import datetime

from pydantic import BaseModel


class ScheduleTypeDTO(BaseModel):
    """A church service, as the rota needs it.

    ``weekday`` is ``1 = Sunday … 7 = Saturday`` — convert with
    ``core.domain.weekday`` before comparing against ``datetime.weekday()``.

    Annotations are qualified as ``datetime.time`` because the ``time`` field would
    otherwise shadow the type on the line below it. The field keeps its name: it is
    what the rota response exposes.
    """

    id: int
    name: str
    weekday: int
    time: datetime.time
    end_time: datetime.time
    active: bool
    takes_rota: bool


class MemberConfigDTO(BaseModel):
    member_id: int
    member_name: str
    weight: int


class MonthlyScheduleDTO(BaseModel):
    date: datetime.date
    member_id: int
    member_name: str
    schedule_type_id: int
    schedule_type_name: str
    schedule_type_time: datetime.time
