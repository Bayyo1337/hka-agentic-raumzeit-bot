# GDPR Opt-In Onboarding & Menu Harmonization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a strict Opt-In flow for new users, seamless message resumption, and update Telegram Auto-Complete menus.

**Architecture:** Extend the `users` table to track consent status and store pending messages. Update the main message handler to act as a gatekeeper, requesting consent before processing. Update the `_USER_COMMANDS` and `_ADMIN_COMMANDS` lists to reflect all available commands.

**Tech Stack:** Python 3.11+, aiosqlite, python-telegram-bot.

---

### Task 1: Database Schema Update

**Files:**
- Modify: `src/db.py`
- Modify: `tests/test_privacy.py`

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_privacy.py
@pytest.mark.asyncio
async def test_opt_in_gatekeeper_db():
    user_id = 99999
    await db.upsert_user(user_id, "testuser", "Test")
    
    # Should default to 0
    status = await db.get_consent_status(user_id)
    assert status == 0
    
    # Update status
    await db.set_consent_status(user_id, 1)
    status = await db.get_consent_status(user_id)
    assert status == 1
    
    # Pending message
    await db.save_pending_message(user_id, "Hello Bot")
    msg = await db.get_and_clear_pending_message(user_id)
    assert msg == "Hello Bot"
    
    # Should be cleared
    msg_empty = await db.get_and_clear_pending_message(user_id)
    assert msg_empty == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_privacy.py::test_opt_in_gatekeeper_db -v`
Expected: FAIL (functions not defined)

- [ ] **Step 3: Update `users` table and add migrations**

```python
# In src/db.py, inside init(), update the users table creation:
            CREATE TABLE IF NOT EXISTS users (
                user_id           INTEGER PRIMARY KEY,
                username          TEXT NOT NULL DEFAULT '',
                first_name        TEXT NOT NULL DEFAULT '',
                banned            INTEGER NOT NULL DEFAULT 0,
                custom_rate_limit INTEGER NOT NULL DEFAULT -1,
                last_seen         TEXT NOT NULL DEFAULT '',
                primary_course    TEXT,
                pending_intent    TEXT,
                missing_entities  TEXT,
                has_consented     INTEGER NOT NULL DEFAULT 0,
                pending_message   TEXT NOT NULL DEFAULT ''
            );

# Below the existing migrations in init():
        try:
            await db.execute("ALTER TABLE users ADD COLUMN has_consented INTEGER NOT NULL DEFAULT 0")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN pending_message TEXT NOT NULL DEFAULT ''")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
```

- [ ] **Step 4: Implement DB helpers**

```python
# In src/db.py (add near other user methods)
async def get_consent_status(user_id: int) -> int:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute("SELECT has_consented FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0

async def set_consent_status(user_id: int, status: int) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("UPDATE users SET has_consented=? WHERE user_id=?", (status, user_id))
        await db.commit()

async def save_pending_message(user_id: int, msg: str) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("UPDATE users SET pending_message=? WHERE user_id=?", (msg, user_id))
        await db.commit()

async def get_and_clear_pending_message(user_id: int) -> str:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute("SELECT pending_message FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        msg = row[0] if row else ""
        if msg:
            await db.execute("UPDATE users SET pending_message='' WHERE user_id=?", (user_id,))
            await db.commit()
    return msg
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_privacy.py::test_opt_in_gatekeeper_db -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/db.py tests/test_privacy.py
git commit -m "db: add consent and pending_message columns with helpers"
```

---

### Task 2: Implement the Gatekeeper in `handle_message`

**Files:**
- Modify: `src/bot.py`

- [ ] **Step 1: Update `handle_message`**

```python
# In src/bot.py, inside handle_message, immediately after `await db.upsert_user(user_id, user.username or "", user.first_name or "")`:

    if not admin._is_admin(user_id) and await db.is_banned(user_id):
        await update.message.reply_text("⛔ Du wurdest gesperrt.")
        return

    # GATEKEEPER
    has_consented = await db.get_consent_status(user_id)
    if has_consented == 0:
        await db.save_pending_message(user_id, text)
        keyboard = [
            [InlineKeyboardButton("✅ Ich stimme zu", callback_data="privacy_opt_in")],
            [InlineKeyboardButton("📄 Details lesen", callback_data="privacy_opt_in_details")]
        ]
        await update.message.reply_text(
            "🏫 *Willkommen beim Raumzeit KI-Bot!*\n\n"
            "Damit ich deine Fragen in natürlicher Sprache beantworten kann, muss ich:\n"
            "1. Deine Nachrichten an unsere KI-Anbieter (z.B. Mistral/OpenAI) weiterleiten.\n"
            "2. Einen Chat-Verlauf speichern, damit die KI den Kontext versteht.\n"
            "3. Ein Basis-Profil (Telegram-ID) für Rate-Limiting anlegen.\n\n"
            "Ohne diese Daten kann der Bot nicht funktionieren. Du kannst später Details via `/consent` "
            "anpassen oder via `/delete` alles löschen.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return
```

- [ ] **Step 2: Add callbacks for the gatekeeper**

```python
# In src/bot.py, at the beginning of handle_callback:

    if data == "privacy_opt_in_details":
        await query.edit_message_text(
            "Alle Informationen zum Datenschutz findest du hier:\n\n"
            "Nutze den Befehl `/privacy`, um die Details direkt im Chat zu lesen, oder besuche "
            "[GitHub](https://github.com/Bayyo1337/hka-agentic-raumzeit-bot/blob/gemini/docs/DSGVO.md).\n\n"
            "Bist du mit der Verarbeitung einverstanden?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Ich stimme zu", callback_data="privacy_opt_in")]]),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        return

    if data == "privacy_opt_in":
        await db.set_consent_status(user_id, 1)
        pending_msg = await db.get_and_clear_pending_message(user_id)
        
        await query.edit_message_text("✅ Danke für deine Zustimmung! Ich verarbeite nun deine erste Anfrage...")
        
        if pending_msg:
            # Re-inject the pending message into the processing flow
            # We can do this by constructing a fake update object or extracting the processing logic.
            # To avoid large refactoring, we'll just call `_process_user_message` (we will extract it next).
            await _process_user_message(update, context, chat_id, user_id, user, pending_msg)
        return
```

- [ ] **Step 3: Extract message processing logic**

Extract the remainder of `handle_message` (from `if _maintenance[0]` onwards) into a new async function `_process_user_message`:

```python
# In src/bot.py, define a new function below handle_message:
async def _process_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, user, text: str) -> None:
    if _maintenance[0] and not admin._is_admin(user_id):
        await update.message.reply_text(_maintenance[1])
        return

    # ... rest of the original handle_message logic ...
```

Update `handle_message` to call it if `has_consented == 1`:
```python
    # After gatekeeper check in handle_message
    await _process_user_message(update, context, chat_id, user_id, user, text)
```

- [ ] **Step 4: Verify syntax**
Run: `uv run python -m py_compile src/bot.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/bot.py
git commit -m "feat: implement strict opt-in gatekeeper and seamless resumption"
```

---

### Task 3: Update Menus and Help Texts

**Files:**
- Modify: `src/bot.py`

- [ ] **Step 1: Update `build_start_text`**

```python
# In src/bot.py, update build_start_text():
        "🚀 *Erste Schritte:*\n"
        "1️⃣ Nutze `/setcourse`, um dein Semester zu hinterlegen.\n"
        "2️⃣ Frag mich: _\"Was habe ich heute?\"_\n"
        "3️⃣ Passe bei Bedarf mit `/consent` deine Datenschutzeinstellungen an.\n\n"
```

- [ ] **Step 2: Update `build_help_text`**

```python
# In src/bot.py, update build_help_text(), replacing the existing lines for /help, /mensa, etc. with:
        "📜 *Basis-Befehle:*",
        "`/help` – Diese Referenz anzeigen",
        "`/mensa` – Heutiger Speiseplan (Moltke)",
        "`/bug` – Fehler melden oder Feedback geben (interaktiv)",
        "`/reset` – Aktuellen Gesprächskontext löschen",
        "`/stats` – Deine Token-Verbrauch & gespeicherte Kurse",
        "",
        "🔒 *Datenschutz & DSGVO:*",
        "`/privacy` – Datenschutzerklärung anzeigen",
        "`/consent` – Privacy-Einstellungen verwalten (Opt-In/Out)",
        "`/data` – Übersicht deiner gespeicherten Daten",
        "`/export` – Daten-Export als JSON anfordern",
        "`/delete` – Alle deine Daten unwiderruflich löschen",
        "`/retention` – Aufbewahrungsfristen anpassen",
        "",
```

- [ ] **Step 3: Update `_USER_COMMANDS`**

```python
# In src/bot.py, update _USER_COMMANDS:
_USER_COMMANDS = [
    BotCommand("start", "Erste Schritte & Beispiele"),
    BotCommand("help", "Alle Befehle & Hilfe"),
    BotCommand("privacy", "Datenschutz & DSGVO"),
    BotCommand("consent", "Privacy-Einstellungen"),
    BotCommand("data", "Deine Daten (DSGVO)"),
    BotCommand("export", "Daten-Export (JSON)"),
    BotCommand("delete", "Alle Daten löschen"),
    BotCommand("retention", "Aufbewahrungsfristen anpassen"),
    BotCommand("setcourse", "Studiengang & Filter einstellen"),
    BotCommand("myplan", "Dein persönlicher Stundenplan"),
    BotCommand("mensa", "Speiseplan der Mensa Moltke"),
    BotCommand("stats", "Dein Profil & Token-Verbrauch"),
    BotCommand("bug", "Fehler melden / Feedback geben"),
    BotCommand("reset", "KI-Gedächtnis löschen"),
]
```

- [ ] **Step 4: Update `_ADMIN_COMMANDS`**

```python
# In src/bot.py, update _ADMIN_COMMANDS:
_ADMIN_COMMANDS = _USER_COMMANDS + [
    BotCommand("admin", "System- & Nutzerübersicht"),
    BotCommand("sync", "Datenbank-Abgleich mit HKA"),
    BotCommand("rooms", "Liste aller bekannten Räume"),
    BotCommand("ping", "API Erreichbarkeit prüfen"),
    BotCommand("indexage", "Alter des Kurs-Index prüfen"),
    BotCommand("courses", "Kurse für ein Kürzel auflisten"),
    BotCommand("feedback", "Aktuelle Fehlerberichte anzeigen"),
    BotCommand("delfeedback", "Einen Fehlerbericht löschen"),
    BotCommand("user", "Nutzer-Details & Limits"),
    BotCommand("ban", "Nutzer sperren"),
    BotCommand("unban", "Nutzer entsperren"),
    BotCommand("resetlimit", "Rate-Limit für Nutzer zurücksetzen"),
    BotCommand("setlimit", "Individuelles Rate-Limit setzen"),
    BotCommand("cleartokens", "Token-Zähler für Nutzer nullen"),
    BotCommand("clearhistory", "Gesprächsverlauf löschen"),
    BotCommand("broadcast", "Nachricht an alle Nutzer senden"),
    BotCommand("setprovider", "KI-Provider wechseln"),
    BotCommand("loglevel", "Logging-Detailtiefe ändern"),
    BotCommand("togglepersonal", "Feature: Personalisierung umschalten"),
    BotCommand("togglemap", "Feature: Lageplan umschalten"),
    BotCommand("maintenance", "Wartungsmodus steuern"),
]
```

- [ ] **Step 5: Verify syntax**
Run: `uv run python -m py_compile src/bot.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/bot.py
git commit -m "feat: harmonize telegram auto-complete menus and help texts"
```
