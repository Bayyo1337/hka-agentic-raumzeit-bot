# GDPR Full Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harmonize privacy documentation, implement granular consent for error reporting, and migrate feedback to structured JSON for full GDPR Export/Delete support.

**Architecture:** Extend the `user_privacy_settings` table, transition `issues/active/` Markdown to `data/feedback/` JSON, and update the bot's error handler to respect the new consent flag and PII redaction.

**Tech Stack:** Python 3.11+, aiosqlite, python-telegram-bot.

---

### Task 1: Database Schema Update

**Files:**
- Modify: `src/db.py`

- [ ] **Step 1: Update `user_privacy_settings` table definition**
Add `allow_error_reports` to the `CREATE TABLE` script and default it to `0`.

```python
# In src/db.py (init function)
CREATE TABLE IF NOT EXISTS user_privacy_settings (
    user_id               INTEGER PRIMARY KEY,
    allow_profile         INTEGER NOT NULL DEFAULT 1,
    allow_history         INTEGER NOT NULL DEFAULT 1,
    allow_llm             INTEGER NOT NULL DEFAULT 1,
    allow_telemetry       INTEGER NOT NULL DEFAULT 1,
    allow_error_reports   INTEGER NOT NULL DEFAULT 0, -- NEW
    history_ttl_hours     INTEGER NOT NULL DEFAULT 168,
    telemetry_ttl_hours   INTEGER NOT NULL DEFAULT 24,
    plan_cache_ttl_hours  INTEGER NOT NULL DEFAULT 4,
    feedback_ttl_days     INTEGER NOT NULL DEFAULT 30,
    updated_at            TEXT NOT NULL DEFAULT ''
);
```

- [ ] **Step 2: Add migration for existing databases**
Add a `try-except` block to add the column if it's missing.

```python
# In src/db.py (init function migration section)
try:
    await db.execute("ALTER TABLE user_privacy_settings ADD COLUMN allow_error_reports INTEGER NOT NULL DEFAULT 0")
except Exception as e:
    if "duplicate column name" not in str(e).lower():
        log.error("Migration failed (allow_error_reports): %s", e)
```

- [ ] **Step 3: Update `get_privacy_settings` and `set_privacy_settings` helpers**
Ensure the new field is read from and written to the database.

- [ ] **Step 4: Verify with a script**
Run: `uv run python -c "import asyncio; from src import db; asyncio.run(db.init())"`
Expected: Success, no migration errors.

- [ ] **Step 5: Commit**
`git add src/db.py && git commit -m "db: add allow_error_reports to privacy settings"`

---

### Task 2: Migration to JSON Feedback

**Files:**
- Modify: `src/db.py`
- Modify: `src/admin.py`

- [ ] **Step 1: Implement JSON feedback saving in `src/db.py`**
Replace/Update `save_feedback_log` to use a consistent naming and format.

```python
# In src/db.py
async def save_feedback_json(data: dict) -> str:
    user_id = data.get("user_id", 0)
    os.makedirs("data/feedback", exist_ok=True)
    # Format: DD.MM.YYYY HH:MM:SS for the content, but filename needs to be sortable
    now = datetime.now()
    ts_file = now.strftime("%Y-%m-%d_%H%M%S")
    path = f"data/feedback/{ts_file}_{user_id}_{data.get('type', 'bug')}.json"
    
    # Ensure timestamp in content is German format
    data["timestamp"] = now.strftime("%d.%m.%Y %H:%M:%S")
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
```

- [ ] **Step 2: Refactor `src/admin.py` to use the new JSON helper**
Update `save_issue_from_log` and `save_user_issue` to call `db.save_feedback_json`.

- [ ] **Step 3: Update Admin commands `/feedback` and `/delfeedback`**
Ensure they work with the new file structure.

- [ ] **Step 4: Commit**
`git add src/db.py src/admin.py && git commit -m "feat: migrate feedback storage to structured JSON"`

---

### Task 3: Granular Error Reporting & Redaction

**Files:**
- Modify: `src/bot.py`
- Modify: `src/agent.py`

- [ ] **Step 1: Harden PII Redaction**
Verify `src/agent.py:redact_pii` includes the improved regex from brainstorming.

- [ ] **Step 2: Update `_error_handler` in `src/bot.py`**
Check `allow_error_reports` and apply redaction.

```python
# In src/bot.py (_error_handler)
settings = await db.get_privacy_settings(uid)
can_report = settings.get("allow_error_reports", 0)

safe_input = agent.redact_pii(user_input)
if not can_report:
    safe_input = "[REDACTED]"
    report_uid = 0
else:
    report_uid = uid

# Save as JSON via updated admin helper
```

- [ ] **Step 4: Commit**
`git add src/bot.py src/agent.py && git commit -m "feat: implement granular consent for error reporting"`

---

### Task 4: GDPR Lifecycle (Export/Delete/Cleanup)

**Files:**
- Modify: `src/db.py`

- [ ] **Step 1: Update `export_user_data`**
Ensure it reads from `data/feedback/*.json` and correctly filters by `user_id`.

- [ ] **Step 2: Update `delete_user_data`**
Ensure it removes all JSON files in `data/feedback/` for that `user_id`.

- [ ] **Step 3: Update `run_gdpr_cleanup`**
Join `user_privacy_settings` to get individual `telemetry_ttl_hours` and `feedback_ttl_days`.

- [ ] **Step 4: Commit**
`git add src/db.py && git commit -m "feat: enforce per-user TTL and full export/delete for feedback"`

---

### Task 5: Text Harmonization & Documentation

**Files:**
- Modify: `src/privacy.py`
- Modify: `docs/DSGVO.md`

- [ ] **Step 1: Update `src/privacy.py` texts**
Remove "encrypted" and "German server" claims. Add `allow_error_reports` to the `/consent` menu and `/data` summary.

- [ ] **Step 2: Update `docs/DSGVO.md`**
Sync data inventory and retention table with the actual implementation.

- [ ] **Step 3: Commit**
`git add src/privacy.py docs/DSGVO.md && git commit -m "docs: harmonize privacy texts and DSGVO documentation"`

---

### Task 6: Verification & Tests

**Files:**
- Modify: `tests/test_privacy.py`

- [ ] **Step 1: Add tests for error reporting consent**
- [ ] **Step 2: Add tests for feedback export/delete**
- [ ] **Step 3: Add tests for per-user TTL cleanup**
- [ ] **Step 4: Run all tests**
Run: `pytest tests/test_privacy.py -v`
Expected: 100% PASS.

- [ ] **Step 5: Final Check**
Run: `uv run python -m py_compile src/*.py`
Expected: No syntax errors.
