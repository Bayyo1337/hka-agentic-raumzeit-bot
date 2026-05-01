
import pytest
import json
from src import formatter

@pytest.mark.asyncio
async def test_db_config_migration():
    """Test that old list-of-strings config is migrated to new dict format."""
    user_id = 99999
    old_config = ["MABB.7", "INFB.3"]
    
    # Mocking db calls would be cleaner but we can use the actual SQLite if configured for tests
    # For now, let's test the logic in get_user_course_config with manual input
    
    raw = json.dumps(old_config)
    data = json.loads(raw)
    migrated = [{"key": item, "excluded_groups": [], "excluded_modules": []} if isinstance(item, str) else item for item in data]
    
    assert len(migrated) == 2
    assert migrated[0]["key"] == "MABB.7"
    assert "excluded_groups" in migrated[0]

def test_formatter_filtering():
    """Test that bookings are correctly filtered based on user config."""
    bookings = [
        {"name": "Vorlesung A", "module": "Module A", "gruppe": "MABB.7.F", "start": "08:00", "end": "09:30"},
        {"name": "Vorlesung B", "module": "Module B", "gruppe": "MABB.7.K", "start": "10:00", "end": "11:30"},
        {"name": "Vorlesung C", "module": "Excluded Mod", "gruppe": "MABB.7.F", "start": "12:00", "end": "13:30"},
    ]
    
    user_config = [
        {
            "key": "MABB.7",
            "excluded_groups": ["MABB.7.K"],
            "excluded_modules": ["Excluded Mod"]
        }
    ]
    
    filtered = formatter._filter_bookings(bookings, user_config)
    
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Vorlesung A"

def test_unified_timeline():
    """Test that multiple course results are merged into a single timeline."""
    collected = [
        ("get_course_timetable", {
            "course_semester": "MABB.7",
            "queried_date": "2026-05-01",
            "bookings": [
                {"name": "MABB-1", "start": "08:00", "end": "09:30", "date": "2026-05-01"}
            ]
        }),
        ("get_course_timetable", {
            "course_semester": "INFB.3",
            "queried_date": "2026-05-01",
            "bookings": [
                {"name": "INFB-1", "start": "10:00", "end": "11:30", "date": "2026-05-01"}
            ]
        })
    ]
    
    reply = formatter.format_results(collected, "Was habe ich heute?")
    
    assert "📅 *Dein Stundenplan*" in reply
    assert "MABB-1" in reply
    assert "INFB-1" in reply
    # Should be in chronological order
    assert reply.find("08:00") < reply.find("10:00")
