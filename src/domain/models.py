from datetime import date, datetime, time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .errors import ErrorCode


class Intent(StrEnum):
    ROOM_TIMETABLE = "room_timetable"
    COURSE_TIMETABLE = "course_timetable"
    SMALLTALK = "smalltalk_fallback"


class SourceStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    ERROR = "error"


class TimetableEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime
    name: str
    room: str | None = None
    source: str = "raumzeit"


class TimetableResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    events: tuple[TimetableEvent, ...] = ()
    fetched_at: datetime
    status: SourceStatus = SourceStatus.FRESH


class IntentRequest(BaseModel):
    intent: Intent
    room: str | None = None
    course: str | None = None
    day: date | None = None
    confidence: float = Field(ge=0, le=1)


class PipelineTrace(BaseModel):
    intent: Intent
    entities: dict[str, str] = Field(default_factory=dict)
    use_case: str
    source: str | None = None
    result: str
    response: str


class PipelineResponse(BaseModel):
    text: str
    trace: PipelineTrace
    error: ErrorCode | None = None


class ConversationState(BaseModel):
    chat_id: int
    intent: Intent | None = None
    entities: dict[str, str] = Field(default_factory=dict)
    expected_entity: str | None = None
    original_message: str | None = None
    attempts: int = Field(default=0, ge=0)
    expires_at: datetime | None = None


class AdapterResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    payload: object
    fetched_at: datetime
    status: SourceStatus


class Person(BaseModel):
    name: str
    email: str | None = None
    account: str | None = None
    room: str | None = None
    office_hours: str | None = None


class Meal(BaseModel):
    meal_id: str
    name: str
    price: str | None = None
    allergens: tuple[str, ...] = ()
    additives: tuple[str, ...] = ()
    vegan: bool | None = None
    vegetarian: bool | None = None


def parse_clock(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return time(hour=hour, minute=minute)
