import re
from datetime import date, timedelta
from typing import Awaitable, Callable

from src.domain.errors import DomainError, ErrorCode
from src.domain.models import (
    Intent,
    IntentRequest,
    PipelineResponse,
    PipelineTrace,
)
from src.presentation.markdown import render_timetable
from src.use_cases.timetable import TimetableUseCase

ROOM_RE = re.compile(r"\b[A-Za-z]{1,3}-\d{2,4}\b")
COURSE_RE = re.compile(r"\b[A-Za-z]{2,8}\.\d{1,2}(?:\.[A-Za-z0-9]+)?\b")


class DeterministicPipeline:
    def __init__(
        self,
        timetable: TimetableUseCase,
        llm_classifier: Callable[[str], Awaitable[dict]] | None = None,
    ) -> None:
        self.timetable = timetable
        self.llm_classifier = llm_classifier

    async def handle(self, text: str, *, today: date | None = None) -> PipelineResponse:
        request = await self._parse(text, today=today or date.today())
        entities = {key: value for key, value in {"room": request.room, "course": request.course}.items() if value}
        try:
            if request.intent not in {Intent.ROOM_TIMETABLE, Intent.COURSE_TIMETABLE}:
                response = "Ich kann diese Anfrage derzeit nicht deterministisch zuordnen."
                trace = PipelineTrace(
                    intent=request.intent,
                    entities=entities,
                    use_case="unsupported",
                    result="rejected",
                    response=response,
                )
                return PipelineResponse(text=response, trace=trace, error=ErrorCode.INVALID_REQUEST)
            result = await self.timetable.execute(room=request.room, course=request.course, day=request.day or date.today())
            response = render_timetable(result)
            trace = PipelineTrace(
                intent=request.intent,
                entities=entities,
                use_case="timetable",
                source="raumzeit",
                result="success",
                response=response,
            )
            return PipelineResponse(text=response, trace=trace)
        except DomainError as exc:
            trace = PipelineTrace(
                intent=request.intent,
                entities=entities,
                use_case="timetable",
                result=exc.code.value,
                response=exc.message,
            )
            return PipelineResponse(text=exc.message, trace=trace, error=exc.code)

    async def _parse(self, text: str, *, today: date) -> IntentRequest:
        room_match = ROOM_RE.search(text)
        course_match = COURSE_RE.search(text)
        day = _resolve_day(text, today)
        if room_match:
            return IntentRequest(
                intent=Intent.ROOM_TIMETABLE,
                room=room_match.group(0).upper(),
                day=day,
                confidence=1,
            )
        if course_match:
            return IntentRequest(
                intent=Intent.COURSE_TIMETABLE,
                course=course_match.group(0).upper(),
                day=day,
                confidence=1,
            )
        if self.llm_classifier is not None:
            raw = await self.llm_classifier(text)
            return IntentRequest.model_validate(raw)
        return IntentRequest(intent=Intent.SMALLTALK, day=day, confidence=0)


def _resolve_day(text: str, today: date) -> date:
    lowered = text.casefold()
    if "morgen" in lowered:
        return today + timedelta(days=1)
    if "gestern" in lowered:
        return today - timedelta(days=1)
    return today

