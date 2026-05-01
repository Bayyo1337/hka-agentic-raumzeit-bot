import pytest
from src.router import Router
from src.agent import _extraction_prompt

@pytest.mark.asyncio
async def test_router_avoids_clarification_with_profile():
    router = Router()
    user_context = {"user_id": 123, "primary_course": "[MABB.2]"}
    # Simulated personal query
    result = await router.classify_message("Was habe ich heute?", user_context, {})
    # This might fail initially if router doesn't use primary_course
    assert result.strategy.action == "agent_flow"

def test_agent_extraction_prompt_contains_profile():
    prompt = _extraction_prompt(primary_course="[MABB.2]", intent="course_timetable")
    assert "MABB.2" in prompt
    assert "SEINEN persönlichen Plan" in prompt
