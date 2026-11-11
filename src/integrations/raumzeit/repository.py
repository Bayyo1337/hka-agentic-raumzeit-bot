from datetime import date
from typing import Awaitable, Callable

from src.domain.models import SourceStatus, TimetableResult
from .parsers import parse_timetable_json


class RaumzeitRepository:
    def __init__(
        self,
        fetch_room: Callable[[str, date], Awaitable[object]],
        fetch_course: Callable[[str, date], Awaitable[object]],
    ) -> None:
        self._fetch_room = fetch_room
        self._fetch_course = fetch_course

    async def room_timetable(self, room: str, day: date) -> TimetableResult:
        payload = await self._fetch_room(room, day)
        return TimetableResult(events=parse_timetable_json(payload, day=day), fetched_at=_now(), status=SourceStatus.FRESH)

    async def course_timetable(self, course: str, day: date) -> TimetableResult:
        payload = await self._fetch_course(course, day)
        return TimetableResult(events=parse_timetable_json(payload, day=day), fetched_at=_now(), status=SourceStatus.FRESH)


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)

