import pytest
import json
import os
import shutil
import logging
import pytest_asyncio
from datetime import datetime, timedelta
from src import db

@pytest_asyncio.fixture(autouse=True)
async def db_init():
    # Paths to clear
    dbs = [db.STATE_DB, db.CACHE_DB, db.TELEMETRY_DB]
    feedback_dir = "data/feedback"
    
    def cleanup():
        # Clear databases
        for db_path in dbs:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except Exception:
                    pass
        # Clear feedback directory
        if os.path.exists(feedback_dir):
            try:
                shutil.rmtree(feedback_dir)
            except Exception:
                pass
        os.makedirs(feedback_dir, exist_ok=True)

    cleanup()
    await db.init()
    yield
    cleanup()

@pytest.mark.asyncio
async def test_privacy_settings_defaults():
    # Neue User-ID
    user_id = 99999
    settings = await db.get_privacy_settings(user_id)
    assert settings["allow_profile"] is True
    assert settings["allow_history"] is True
    assert settings["allow_llm"] is True
    assert settings["history_ttl_hours"] == 168
    assert settings["allow_error_reports"] is False

@pytest.mark.asyncio
async def test_privacy_settings_update():
    user_id = 88888
    new_settings = {
        "allow_profile": False,
        "allow_history": False,
        "allow_llm": True,
        "allow_telemetry": True,
        "allow_error_reports": True,
        "history_ttl_hours": 24,
        "telemetry_ttl_hours": 2,
        "plan_cache_ttl_hours": 1,
        "feedback_ttl_days": 7
    }
    await db.set_privacy_settings(user_id, new_settings)
    
    saved = await db.get_privacy_settings(user_id)
    assert saved["allow_profile"] is False
    assert saved["allow_history"] is False
    assert saved["history_ttl_hours"] == 24
    assert saved["allow_error_reports"] is True

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
    from src.privacy import redact_pii
    text = "Meine Email ist test@example.com und meine Nummer 0176 1234567. IBAN DE12345678901234567890."
    redacted = redact_pii(text)
    assert "[EMAIL]" in redacted
    assert "[PHONE]" in redacted
    assert "[IBAN]" in redacted
    assert "test@example.com" not in redacted
    assert "0176" not in redacted

    # Test: Trailing period in Email
    assert redact_pii("Kontakt: info@h-ka.de.") == "Kontakt: [EMAIL]."
    
    # Test: Word boundaries for Phone
    assert redact_pii("ID: 12345678") == "ID: 12345678"  # Should NOT match as phone
    assert redact_pii("Tel: +49 176 1234567") == "Tel: [PHONE]"
    
    # Test: IBAN boundaries
    assert redact_pii("IBANDE1234567890123456789012") == "IBANDE1234567890123456789012" # No boundary

    # --- EDGE CASES ---
    # Case-sensitivity
    assert redact_pii("MAIL@PROVIDER.DE") == "[EMAIL]"
    
    # Multiple PII elements
    multi_text = "Emails: a@b.com, c@d.de; Phone: +49123 456789, 0721-12345"
    multi_redacted = redact_pii(multi_text)
    assert multi_redacted.count("[EMAIL]") == 2
    assert multi_redacted.count("[PHONE]") == 2
    
    # PII immediately followed by punctuation
    assert redact_pii("Call me: +4912345678.") == "Call me: [PHONE]."
    assert redact_pii("Write to: info@h-ka.de!") == "Write to: [EMAIL]!"

@pytest.mark.asyncio
async def test_feedback_json_storage_and_export():
    user_id = 55555
    data = {
        "user_id": user_id,
        "type": "bug",
        "title": "Test Bug",
        "comment": "Something is wrong",
        "context": "N/A"
    }
    
    # Speichern
    filename = await db.save_feedback_json(data)
    assert filename.endswith(".json")
    assert f"_{user_id}_" in filename
    
    path = os.path.join("data/feedback", filename)
    assert os.path.exists(path)
    
    # Export prüfen
    export = await db.export_user_data(user_id)
    assert "feedback_files" in export
    assert len(export["feedback_files"]) >= 1
    assert any(f["filename"] == filename for f in export["feedback_files"])
    
    # Cleanup for next test
    if os.path.exists(path):
        os.remove(path)

@pytest.mark.asyncio
async def test_feedback_deletion():
    user_id = 44444
    data = {"user_id": user_id, "type": "feedback", "text": "Delete me"}
    filename = await db.save_feedback_json(data)
    path = os.path.join("data/feedback", filename)
    assert os.path.exists(path)
    
    # Löschen
    await db.delete_user_data(user_id)
    assert not os.path.exists(path)

@pytest.mark.asyncio
async def test_per_user_cleanup():
    now = datetime.now()
    u1, u2 = 111, 222
    
    # User 1: 1h History TTL, 1h Telemetry, 1h Plan, 1 day Feedback
    await db.set_privacy_settings(u1, {
        "history_ttl_hours": 1,
        "telemetry_ttl_hours": 1,
        "plan_cache_ttl_hours": 1,
        "feedback_ttl_days": 1
    })
    
    # User 2: 100h History TTL (Defaults otherwise)
    await db.set_privacy_settings(u2, {"history_ttl_hours": 100})
    
    # Daten injecten (2h alt)
    two_hours_ago = (now - timedelta(hours=2)).isoformat()
    two_days_ago = (now - timedelta(days=2))
    
    import aiosqlite
    async with aiosqlite.connect(db.STATE_DB) as conn:
        await conn.execute("INSERT INTO histories (chat_id, messages, updated_at) VALUES (?, '[]', ?)", (u1, two_hours_ago))
        await conn.execute("INSERT INTO histories (chat_id, messages, updated_at) VALUES (?, '[]', ?)", (u2, two_hours_ago))
        await conn.commit()
    
    async with aiosqlite.connect(db.TELEMETRY_DB) as conn:
        await conn.execute("INSERT INTO requests (user_id, ts) VALUES (?, ?)", (u1, two_hours_ago))
        await conn.execute("INSERT INTO requests (user_id, ts) VALUES (?, ?)", (u2, two_hours_ago))
        await conn.commit()
        
    async with aiosqlite.connect(db.CACHE_DB) as conn:
        await conn.execute("INSERT INTO user_plan_cache (user_id, plan_json, cached_at) VALUES (?, '{}', ?)", (u1, two_hours_ago))
        await conn.execute("INSERT INTO user_plan_cache (user_id, plan_json, cached_at) VALUES (?, '{}', ?)", (u2, two_hours_ago))
        await conn.commit()

    # Feedback Dateien manuell anlegen und mtime setzen
    os.makedirs("data/feedback", exist_ok=True)
    f1 = os.path.join("data/feedback", f"2026-01-01_120000_{u1}_bug.json")
    f2 = os.path.join("data/feedback", f"2026-01-01_120000_{u2}_bug.json")
    for f in [f1, f2]:
        with open(f, "w") as j: json.dump({"test": 1}, j)
        os.utime(f, (two_days_ago.timestamp(), two_days_ago.timestamp()))

    # Cleanup
    await db.run_gdpr_cleanup()
    
    # Verifizieren
    # User 1: Alles weg (2h > 1h, 2d > 1d)
    assert await db.load_history(u1) == []
    assert await db.get_total_count(u1) == 0
    assert await db.get_user_plan_cache(u1) is None
    assert not os.path.exists(f1)
    
    # User 2: History bleibt (2h < 100h)
    async with aiosqlite.connect(db.STATE_DB) as conn:
        async with conn.execute("SELECT COUNT(*) FROM histories WHERE chat_id=?", (u2,)) as cur:
            (count,) = await cur.fetchone()
            assert count == 1
            
    # Telemetry bleibt (2h < 24h default)
    assert await db.get_total_count(u2) == 1
    # Feedback bleibt (2d < 30d default)
    assert os.path.exists(f2)
    
    # Cleanup files
    if os.path.exists(f2): os.remove(f2)

@pytest.mark.asyncio
async def test_error_reporting_behavior():
    from src.bot import _error_handler
    from unittest.mock import AsyncMock, MagicMock
    
    # User mit Opt-Out
    u_no = 123
    await db.set_privacy_settings(u_no, {"allow_error_reports": False})
    
    # User mit Opt-In
    u_yes = 456
    await db.set_privacy_settings(u_yes, {"allow_error_reports": True})
    
    # Mocking context
    context = MagicMock()
    context.error = Exception("Test Error")
    context.bot.send_message = AsyncMock()
    
    from src.config import settings
    original_admins = settings.admin_user_ids
    settings.admin_user_ids = "999"
    
    try:
        # 1. Test Opt-Out
        update_no = MagicMock()
        update_no.effective_user.id = u_no
        update_no.effective_user.username = "PrivacyUser"
        update_no.effective_message.text = "Mein Passwort ist 12345"
        
        from src import bot
        bot._error_cache = {}
        
        await _error_handler(update_no, context)
        
        assert len(bot._error_cache) == 1
        err_id = list(bot._error_cache.keys())[0]
        report = bot._error_cache[err_id]
        
        assert report["report_uid"] == 0
        assert report["user_info"] == "Anonymous"
        assert "[REDACTED]" in report["user_input"]
        
        # 2. Test Opt-In
        update_yes = MagicMock()
        update_yes.effective_user.id = u_yes
        update_yes.effective_user.username = "HelpfulUser"
        update_yes.effective_message.text = "Hier ist ein Fehler"
        
        bot._error_cache = {}
        await _error_handler(update_yes, context)
        
        assert len(bot._error_cache) == 1
        err_id = list(bot._error_cache.keys())[0]
        report = bot._error_cache[err_id]
        
        assert report["report_uid"] == u_yes
        assert report["user_info"] == "@HelpfulUser"
        assert report["user_input"] == "Hier ist ein Fehler"
    finally:
        settings.admin_user_ids = original_admins

@pytest.mark.asyncio
async def test_opt_in_gatekeeper_db():
    user_id = 33333
    await db.upsert_user(user_id, "testuser", "Test")
    
    # Default status should be 0
    status = await db.get_consent_status(user_id)
    assert status == 0
    
    # Update status to 1
    await db.set_consent_status(user_id, 1)
    status_updated = await db.get_consent_status(user_id)
    assert status_updated == 1
    
    # Test pending message
    await db.save_pending_message(user_id, "Hello World")
    msg = await db.get_and_clear_pending_message(user_id)
    assert msg == "Hello World"
    
    # Assert message is cleared
    cleared_msg = await db.get_and_clear_pending_message(user_id)
    assert cleared_msg == ""

@pytest.mark.asyncio
async def test_consent_gate_no_profile_before_opt_in():
    user_id = 22222
    await db.set_consent_status(user_id, 0)
    profile = await db.get_user(user_id)
    assert profile["username"] == ""
    assert profile["first_name"] == ""
    assert await db.get_consent_status(user_id) == 0

    await db.upsert_user(user_id, "consented_user", "Consented")
    profile = await db.get_user(user_id)
    assert profile["username"] == "consented_user"
    assert profile["first_name"] == "Consented"

@pytest.mark.asyncio
async def test_logging_anonymization(caplog):
    from src import privacy
    logger = logging.getLogger("src.privacy")
    caplog.set_level(logging.INFO, logger="src.privacy")
    anon = privacy.anonymize_user_id(123456)
    logger.info("User %s deleted their data via /delete", anon)
    assert anon in caplog.text
    assert "123456" not in caplog.text
    assert "@testuser" not in caplog.text
