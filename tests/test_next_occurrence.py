import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import asyncio
from src.tools import get_next_occurrence

@pytest.mark.asyncio
async def test_get_next_occurrence_no_module():
    res = await get_next_occurrence("")
    assert "error" in res

@pytest.mark.asyncio
async def test_get_next_occurrence_from_cache():
    now = datetime.now()
    # Event in 2 Tagen -> kein Refetch (da > 24h)
    future_event = {
        "module": "Mathe 1",
        "start": (now + timedelta(hours=48)).isoformat(),
        "date": (now + timedelta(days=2)).date().isoformat(),
        "cancelled": False
    }
    
    mock_cache = {
        "bookings": [future_event]
    }
    
    with patch("src.db.get_user_plan_cache", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = mock_cache
        
        with patch("src.tools.get_course_timetable", new_callable=AsyncMock) as mock_fetch:
            res = await get_next_occurrence("Mathe 1", user_id=123)
            
            assert res["found"] is True
            assert res["next_event"]["module"] == "Mathe 1"
            mock_fetch.assert_not_called()

@pytest.mark.asyncio
async def test_get_next_occurrence_skips_cancelled():
    now = datetime.now()
    cancelled_event = {
        "module": "Mathe 1",
        "start": (now + timedelta(hours=2)).isoformat(),
        "date": now.date().isoformat(),
        "cancelled": True
    }
    future_valid_event = {
        "module": "Mathe 1",
        "start": (now + timedelta(hours=48)).isoformat(),
        "date": (now + timedelta(days=2)).date().isoformat(),
        "cancelled": False
    }
    
    mock_cache = {
        "bookings": [cancelled_event, future_valid_event]
    }
    
    with patch("src.db.get_user_plan_cache", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = mock_cache
        
        with patch("src.tools.get_course_timetable", new_callable=AsyncMock) as mock_fetch:
            res = await get_next_occurrence("Mathe 1", user_id=123)
            
            assert res["found"] is True
            assert res["next_event"]["module"] == "Mathe 1"
            # Es sollte das zukünftige Event sein, nicht das abgesagte
            assert res["next_event"]["start"] == future_valid_event["start"]

@pytest.mark.asyncio
async def test_get_next_occurrence_revalidates_soon_event():
    now = datetime.now()
    # Event in 2 Stunden -> Refetch nötig (da < 24h)
    soon_event = {
        "module": "Mathe 1",
        "start": (now + timedelta(hours=2)).isoformat(),
        "date": now.date().isoformat(),
        "cancelled": False
    }
    
    mock_cache = {
        "bookings": [soon_event]
    }
    
    with patch("src.db.get_user_plan_cache", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = mock_cache
        
        with patch("src.tools.get_course_timetable", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"bookings": [soon_event]}
            with patch("src.db.get_user_course_config", new_callable=AsyncMock) as mock_cfg:
                mock_cfg.return_value = [{"key": "MABB.1"}]
                
                res = await get_next_occurrence("Mathe 1", user_id=123)
                
                assert res["found"] is True
                # Refetch muss aufgerufen worden sein
                mock_fetch.assert_called()

@pytest.mark.asyncio
async def test_get_next_occurrence_no_events():
    with patch("src.db.get_user_plan_cache", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = None
        
        with patch("src.tools.get_course_timetable", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"bookings": []}
            with patch("src.db.get_user_course_config", new_callable=AsyncMock) as mock_cfg:
                mock_cfg.return_value = [{"key": "MABB.1"}]
                
                res = await get_next_occurrence("Informatik", user_id=123)
                assert res["found"] is False
                assert "Keine kommenden Termine" in res["message"]
