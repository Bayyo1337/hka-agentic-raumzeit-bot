from datetime import date
from typing import Protocol

from src.domain.errors import DomainError, ErrorCode
from src.domain.models import TimetableResult


class TimetableRepository(Protocol):
    async def room_timetable(self, room: str, day: date) -> TimetableResult: ...

    async def course_timetable(self, course: str, day: date) -> TimetableResult: ...


class TimetableUseCase:
    def __init__(self, repository: TimetableRepository) -> None:
        self.repository = repository

    async def execute(self, *, room: str | None, course: str | None, day: date) -> TimetableResult:
        if room and course:
            raise DomainError(ErrorCode.INVALID_REQUEST, "Room and course cannot be requested together")
        if room:
            return await self.repository.room_timetable(room, day)
        if course:
            return await self.repository.course_timetable(course, day)
        raise DomainError(ErrorCode.CLARIFICATION_REQUIRED, "A room or course is required")

