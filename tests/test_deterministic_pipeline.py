from datetime import date, datetime, timedelta, timezone

import pytest

from src.app.requests.pipeline import DeterministicPipeline
from src import agent
from src.agent import _deterministic_query
from src.domain.models import TimetableResult
from src.presentation.markdown import chunk_telegram_text, escape_markdown
from src.use_cases.timetable import TimetableUseCase
from src.app.requests.legacy_repository import LegacyToolTimetableRepository


class FakeRepository:
    async def room_timetable(self, room, day):
        return TimetableResult(
            events=(
                {
                    "start": datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc),
                    "end": datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc),
                    "name": "Mathe_1",
                    "room": room,
                },
            ),
            fetched_at=datetime.now(timezone.utc),
        )

    async def course_timetable(self, course, day):
        return TimetableResult(events=(), fetched_at=datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_pipeline_resolves_room_and_relative_date():
    pipeline = DeterministicPipeline(TimetableUseCase(FakeRepository()))
    response = await pipeline.handle("Wann ist m-102 morgen frei?", today=date(2026, 11, 8))
    assert response.trace.entities == {"room": "M-102"}
    assert response.trace.result == "success"
    assert "Mathe\\_1" in response.text


@pytest.mark.asyncio
async def test_pipeline_rejects_unresolved_request():
    pipeline = DeterministicPipeline(TimetableUseCase(FakeRepository()))
    response = await pipeline.handle("Hallo", today=date(2026, 11, 8))
    assert response.error is not None
    assert response.trace.result == "rejected"


def test_markdown_and_chunking():
    assert escape_markdown("a_b") == "a\\_b"
    chunks = chunk_telegram_text("a\nb\nc", limit=3)
    assert "".join(chunks).replace("\n", "") == "abc"
    assert all(len(chunk) <= 3 for chunk in chunks)


def test_agent_resolves_unambiguous_queries_without_llm():
    result = _deterministic_query("Wann ist m-102 morgen frei?")
    assert result is not None
    assert result[0] == "get_room_timetable"
    assert result[1]["room_name"] == "M-102"
    assert result[1]["date"] == (date.today() + timedelta(days=1)).isoformat()
    assert _deterministic_query("Stundenplan MABB 6 am 09.11.2026?") == (
        "get_course_timetable",
        {"course_key": "MABB.6", "date": "2026-11-09"},
    )


@pytest.mark.asyncio
async def test_agent_executes_deterministic_room_query(monkeypatch):
    calls = []

    async def fake_handler(args):
        calls.append(args)
        return {"bookings": []}

    monkeypatch.setitem(agent.TOOL_HANDLERS, "get_room_timetable", fake_handler)
    reply, input_tokens, output_tokens, results = await agent.run("Wann ist M-102 frei?", [])
    assert input_tokens == output_tokens == 0
    assert calls == [{"room_name": "M-102", "date": date.today().isoformat()}]
    assert results[0][0] == "get_room_timetable"
    assert "_pipeline_trace" in results[0][1]
    assert "Keine" in reply


@pytest.mark.asyncio
async def test_legacy_repository_normalizes_bookings():
    async def fetch(_args):
        return {"bookings": [{"start": "08:00", "end": "09:30", "name": "MATH", "room": "M-102"}]}

    result = await LegacyToolTimetableRepository(
        {"get_room_timetable": fetch, "get_course_timetable": fetch}
    ).room_timetable("M-102", date(2026, 11, 8))
    assert result.events[0].name == "MATH"
