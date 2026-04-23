import pytest
from src.router import router_instance, RouterOutput

@pytest.mark.asyncio
async def test_fast_path_room():
    state = {}
    res = await router_instance.classify_message("Wann ist M-102 frei?", {}, state)
    assert res.intent == "room_timetable"
    assert res.confidence == 1.0
    assert res.strategy.action == "direct_tool"

@pytest.mark.asyncio
async def test_fast_path_mensa():
    state = {}
    res = await router_instance.classify_message("Gibt es heute in der Mensa Pommes?", {}, state)
    assert res.intent == "mensa_menu"
    assert res.confidence == 1.0
    assert res.strategy.action == "agent_flow"

@pytest.mark.asyncio
async def test_fast_path_map():
    state = {}
    res = await router_instance.classify_message("Wo ist Gebäude LI?", {}, state)
    assert res.intent == "campus_map"
    assert res.confidence == 1.0
    assert res.strategy.action == "agent_flow"

@pytest.mark.asyncio
async def test_fast_path_calendar():
    state = {}
    res = await router_instance.classify_message("Wann ist die nächste vorlesungsfreie Zeit?", {}, state)
    assert res.intent == "university_calendar"
    assert res.confidence == 1.0
    assert res.strategy.action == "direct_tool"

# Wir mocken litellm für den llm_fallback test
from unittest.mock import patch

@pytest.mark.asyncio
@patch('src.router.litellm.acompletion')
async def test_llm_fallback(mock_acompletion):
    class MockChoice:
        def __init__(self, content):
            self.message = type('obj', (object,), {'content': content})

    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]

    mock_acompletion.return_value = MockResponse(
        '{"intent": "course_timetable", "confidence": 0.8, "entities": {"course": "MABB.6"}, "strategy": {"action": "agent_flow", "reason": "User asks for course schedule"}}'
    )
    
    state = {}
    res = await router_instance.classify_message("Was habe ich heute in Maschinenbau im 6. Semester?", {}, state)
    assert res.intent == "course_timetable"
    assert res.confidence == 0.8
    assert res.strategy.action == "agent_flow"
