from datetime import date, datetime, time, timezone
from typing import Awaitable, Callable

from src.domain.models import SourceStatus, TimetableResult


class LegacyToolTimetableRepository:
    """Adapts the existing tool handlers to the typed timetable contract."""

    def __init__(self, handlers: dict[str, Callable[[dict], Awaitable[dict]]]) -> None:
        self.handlers = handlers
        self.last_payload: dict | None = None

    async def room_timetable(self, room: str, day: date) -> TimetableResult:
        payload = await self.handlers["get_room_timetable"](
            {"room_name": room, "date": day.isoformat()}
        )
        self.last_payload = payload
        return _result_from_legacy(payload, day)

    async def course_timetable(self, course: str, day: date) -> TimetableResult:
        payload = await self.handlers["get_course_timetable"](
            {"course_key": course, "date": day.isoformat()}
        )
        self.last_payload = payload
        return _result_from_legacy(payload, day)


def _result_from_legacy(payload: object, day: date) -> TimetableResult:
    if not isinstance(payload, dict):
        raise ValueError("Legacy timetable tool returned a non-object")
    if payload.get("error"):
        raise ValueError(str(payload["error"]))
    events = []
    for booking in payload.get("bookings", []):
        if not isinstance(booking, dict):
            continue
        start = _booking_datetime(booking.get("start"), day)
        end = _booking_datetime(booking.get("end"), day)
        if start is None or end is None:
            continue
        events.append(
            {
                "start": start,
                "end": end,
                "name": booking.get("module") or booking.get("name") or "Unbenannter Termin",
                "room": booking.get("room"),
            }
        )
    return TimetableResult(
        events=tuple(events),
        fetched_at=datetime.now(timezone.utc),
        status=SourceStatus.FRESH,
    )


def _booking_datetime(value: object, day: date) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, int):
        hours, minutes = divmod(value, 60)
        return datetime.combine(day, time(hours, minutes), tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                hour, minute = (int(part) for part in value[:5].split(":"))
            except (TypeError, ValueError):
                return None
            return datetime.combine(day, time(hour=hour, minute=minute), tzinfo=timezone.utc)
    return None
