from datetime import date
from src.agent import resolve_german_weekday

def test_resolve_german_weekday():
    ref = date(2026, 5, 1) # Friday
    # Montag should be 2026-05-04
    assert resolve_german_weekday("Was gibt es am Montag?", ref) == date(2026, 5, 4)
    # Freitag should be today (2026-05-01)
    assert resolve_german_weekday("Heute ist Freitag", ref) == date(2026, 5, 1)
    # Unknown should return None
    assert resolve_german_weekday("Irgendwann", ref) is None
