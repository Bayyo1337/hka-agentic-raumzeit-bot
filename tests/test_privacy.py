import pytest
import json
import os
import pytest_asyncio
from datetime import datetime, timedelta
from src import db

@pytest_asyncio.fixture(autouse=True)
async def db_init():
    await db.init()
    yield

@pytest.mark.asyncio
async def test_privacy_settings_defaults():
    # Neue User-ID
    user_id = 99999
    settings = await db.get_privacy_settings(user_id)
    assert settings["allow_profile"] == 1
    assert settings["allow_history"] == 1
    assert settings["allow_llm"] == 1
    assert settings["history_ttl_hours"] == 168
    assert settings["allow_error_reports"] == 0

@pytest.mark.asyncio
async def test_privacy_settings_update():
    user_id = 88888
    new_settings = {
        "allow_profile": 0,
        "allow_history": 0,
        "allow_llm": 1,
        "allow_telemetry": 1,
        "allow_error_reports": 1,
        "history_ttl_hours": 24,
        "telemetry_ttl_hours": 2,
        "plan_cache_ttl_hours": 1,
        "feedback_ttl_days": 7
    }
    await db.set_privacy_settings(user_id, new_settings)
    
    saved = await db.get_privacy_settings(user_id)
    assert saved["allow_profile"] == 0
    assert saved["allow_history"] == 0
    assert saved["history_ttl_hours"] == 24
    assert saved["allow_error_reports"] == 1

@pytest.mark.asyncio
async def test_user_data_export_and_delete():
    user_id = 77777
    chat_id = user_id
    
    # Daten anlegen
    await db.upsert_user(user_id, "testuser", "Test")
    await db.save_history(chat_id, [{"role": "user", "content": "Hallo"}])
    await db.add_tokens(user_id, 100, 50)
    
    # Export prüfen
    export = await db.export_user_data(user_id)
    assert export["user_id"] == user_id
    assert len(export["history"]) == 1
    assert export["history"][0]["content"] == "Hallo"
    
    # Löschen
    await db.delete_user_data(user_id)
    
    # Verifizieren
    profile = await db.get_user(user_id)
    assert profile is None
    history = await db.load_history(chat_id)
    assert history == []
    tokens = await db.get_tokens(user_id)
    assert tokens == (0, 0)

@pytest.mark.asyncio
async def test_gdpr_cleanup():
    user_id = 66666
    # Altes Datum simulieren
    old_ts = (datetime.now() - timedelta(days=10)).isoformat()
    
    # Settings mit 24h TTL
    await db.set_privacy_settings(user_id, {"history_ttl_hours": 24})
    
    # Alte History in DB injecten (via SQL da save_history 'now' nutzt)
    import aiosqlite
    async with aiosqlite.connect(db.STATE_DB) as conn:
        await conn.execute(
            "INSERT INTO histories (chat_id, messages, updated_at) VALUES (?, ?, ?)",
            (user_id, json.dumps([{"role": "user", "content": "Alt"}]), old_ts)
        )
        await conn.commit()
    
    # Cleanup laufen lassen
    stats = await db.run_gdpr_cleanup()
    assert stats["histories"] >= 1
    
    # Prüfen ob weg
    history = await db.load_history(user_id)
    assert history == []

def test_pii_redaction():
    from src.agent import redact_pii
    text = "Meine Email ist test@example.com und meine Nummer 0176 1234567. IBAN DE12345678901234567890."
    redacted = redact_pii(text)
    assert "[EMAIL]" in redacted
    assert "[PHONE]" in redacted
    assert "[IBAN]" in redacted
    assert "test@example.com" not in redacted
    assert "0176" not in redacted
