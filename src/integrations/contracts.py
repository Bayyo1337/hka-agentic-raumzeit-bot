from datetime import date
from typing import Protocol

from src.domain.models import AdapterResponse, TimetableResult


class RaumzeitAdapter(Protocol):
    async def room_timetable(self, room: str, day: date) -> AdapterResponse: ...

    async def course_timetable(self, course: str, day: date) -> AdapterResponse: ...


class HkaPeopleAdapter(Protocol):
    async def find_person(self, query: str) -> AdapterResponse: ...


class MensaAdapter(Protocol):
    async def menu(self, canteen: str, day: date) -> AdapterResponse: ...


def timetable_from_response(response: AdapterResponse) -> TimetableResult:
    if not isinstance(response.payload, TimetableResult):
        raise TypeError("Adapter response payload is not a TimetableResult")
    return response.payload.model_copy(update={"fetched_at": response.fetched_at, "status": response.status})
