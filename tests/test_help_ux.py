import pytest
from src.bot import build_help_text, build_start_text
from src.state import _personal_features

def test_start_text_content():
    original = _personal_features[0]
    _personal_features[0] = True
    try:
        text = build_start_text()
        assert "Willkommen" in text
        assert "/setcourse" in text
        assert "Mensa" in text
        assert "MABB.2" in text
    finally:
        _personal_features[0] = original

def test_help_text_user():
    # Ensure it's ON for this test
    original = _personal_features[0]
    _personal_features[0] = True
    try:
        text = build_help_text(is_admin=False)
        assert "Raumzeit KI-Bot Hilfe" in text
        assert "/mensa" in text
        assert "/setcourse" in text
        assert "Admin-Bereich" not in text
        assert "/sync" not in text
    finally:
        _personal_features[0] = original

def test_help_text_admin():
    text = build_help_text(is_admin=True)
    assert "Raumzeit KI-Bot Hilfe" in text
    assert "Admin-Bereich" in text
    assert "/sync" in text
    assert "/loglevel" in text

def test_help_text_no_personalization():
    # Toggle off
    original = _personal_features[0]
    _personal_features[0] = False
    try:
        text = build_help_text(is_admin=False)
        assert "Studium & Personalisierung" not in text
        assert "/setcourse" not in text
    finally:
        _personal_features[0] = original

def test_admin_help_parameters():
    text = build_help_text(is_admin=True)
    assert "/sync [all|courses|lecturers]" in text
    assert "/loglevel [DEBUG|INFO|WARNING]" in text
    assert "/broadcast [Text]" in text
