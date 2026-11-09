from datetime import date, datetime, time, timedelta

from src.domain.errors import DomainError, ErrorCode
from src.domain.models import TimetableEvent


def parse_timetable_json(payload: object, *, day: date) -> tuple[TimetableEvent, ...]:
    if not isinstance(payload, list):
        raise DomainError(ErrorCode.SOURCE_ERROR, "Raumzeit timetable response is not a list")

    events: list[TimetableEvent] = []
    for item in payload:
        if not isinstance(item, dict):
            raise DomainError(ErrorCode.SOURCE_ERROR, "Raumzeit timetable item is not an object")
        try:
            start = _parse_datetime(item.get("start", item.get("startTime")), day)
            end = _parse_datetime(item.get("end", item.get("endTime")), day)
            name = str(item.get("name", item.get("longName", ""))).strip()
            if not name:
                raise ValueError("empty event name")
        except (KeyError, TypeError, ValueError) as exc:
            raise DomainError(ErrorCode.SOURCE_ERROR, "Invalid timetable event") from exc
        events.append(
            TimetableEvent(
                start=start,
                end=end,
                name=name,
                room=_optional_text(item.get("room")),
            )
        )
    return tuple(sorted(events, key=lambda event: (event.start, event.end, event.name)))


def _parse_datetime(value: object, day: date) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, int):
        return datetime.combine(day, time.min) + timedelta(minutes=value)
    if not isinstance(value, str):
        raise TypeError("datetime must be a string or minutes")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        if len(value) == 5 and value[2] == ":":
            hour, minute = (int(part) for part in value.split(":", 1))
            return datetime.combine(day, datetime.min.time().replace(hour=hour, minute=minute))
        raise


def parse_course_ical(text: str, *, year: int) -> tuple[TimetableEvent, ...]:
    events: list[TimetableEvent] = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("#", 4)
        if len(parts) != 5:
            continue
        weekday, start_minutes, end_minutes, course_id, name = parts
        try:
            weekday_number = int(weekday)
            start = int(start_minutes)
            end = int(end_minutes)
        except ValueError as exc:
            raise DomainError(ErrorCode.SOURCE_ERROR, "Invalid course calendar row") from exc
        if not 0 <= weekday_number <= 6 or not 0 <= start < end <= 24 * 60:
            raise DomainError(ErrorCode.SOURCE_ERROR, "Course calendar time is out of range")
        event_day = date.fromisocalendar(year, 1, 1) + timedelta(days=weekday_number)
        events.append(
            TimetableEvent(
                start=datetime.combine(event_day, datetime.min.time()) + timedelta(minutes=start),
                end=datetime.combine(event_day, datetime.min.time()) + timedelta(minutes=end),
                name=f"{course_id}: {name.strip()}",
            )
        )
    return tuple(events)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
