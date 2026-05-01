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

def test_formatter_no_confirm_on_personal_empty():
    from src.formatter import format_results, CONFIRM_SENTINEL
    # Simulated personal results with NO bookings
    collected = [("get_course_timetable", {"course_semester": "MABB.2", "bookings": [], "queried_date": "2026-05-01"})]
    
    # CASE 1: is_personal=True -> Should NOT have CONFIRM_SENTINEL
    reply = format_results(collected, "Was habe ich heute?", is_personal=True)
    assert CONFIRM_SENTINEL not in reply
    assert "Keine" in reply
    
    # CASE 2: is_personal=False -> Should HAVE CONFIRM_SENTINEL (Legacy behavior)
    # Note: Currently format_results might not pass is_personal to _fmt_course, 
    # so we'll need to fix that.
    reply_explicit = format_results(collected, "Stundenplan MABB.2", is_personal=False)
    assert CONFIRM_SENTINEL in reply_explicit

def test_next_week_date_logic():
    from src.tools import _next_week_range
    from datetime import date, timedelta
    
    # We can't easily mock date.today() without freezegun, 
    # but we can verify the properties of the result.
    d_from, d_to = _next_week_range()
    
    start = date.fromisoformat(d_from)
    end = date.fromisoformat(d_to)
    
    # 1. Start must be a Monday (weekday 0)
    assert start.weekday() == 0
    # 2. End must be a Friday (weekday 4)
    assert end.weekday() == 4
    # 3. Difference must be 4 days
    assert (end - start).days == 4
    # 4. Start must be in the future
    assert start > date.today()
    # 5. Start must be within the next 7 days
    assert (start - date.today()).days <= 7

@pytest.mark.asyncio
async def test_get_course_timetable_next_week_logic():
    from src.tools import get_course_timetable
    from unittest.mock import patch, AsyncMock
    
    with patch("src.tools._fetch_ical", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = []
        with patch("src.db.get_course_variants", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = ["MABB.2"]
            
            res = await get_course_timetable("MABB.2", date="next_week")
            
            # Verify that _fetch_ical was called with date_from and date_to
            args, kwargs = mock_fetch.call_args
            assert "date_from" in kwargs
            assert "date_to" in kwargs
            
            assert "Nächste Woche" in res["queried_date"]
