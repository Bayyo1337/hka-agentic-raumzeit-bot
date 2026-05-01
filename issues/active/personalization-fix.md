# Personalization & Personal Schedule Fix

## Status
- **Root Cause Identified**: Generic course keys (e.g. MABB.3) caused empty results from HKA API; Router over-clarified "vague" personal questions.
- **Fix Applied**: Variant-aware wizard in `/setcourses`; Profile-aware Router logic; `httpx.ReadError` resilience.
- **Verification**: 8/8 tests passed (Personalization & Config).

## Changes

### 1. Variant-Aware Wizard (`src/bot.py`)
- When adding a course (e.g., `MABB.3`), the bot now checks the `course_index` for variants.
- If multiple variants exist (e.g., `MABB.3.E`, `MABB.3.Z`), it presents an inline keyboard for selection.
- This ensures users store "real" keys that actually contain booking data.

### 2. Router Profile-Awareness (`src/router.py` & `src/agent.py`)
- The Router now checks if the user has a stored profile.
- For personal queries (ich, mein, heute, morgen, wann habe ich), it bypasses `ask_clarification` and forces `agent_flow`.
- `agent.py` extraction rules prioritized stored courses for these queries.

### 3. Formatting & Feedback (`src/formatter.py`)
- Suppressed "❓ Stimmt das so?" (CONFIRM_SENTINEL) for personal queries that return empty results to avoid frustrating feedback loops.

### 4. Polling Resilience (`src/bot.py`)
- Specifically catch `httpx.ReadError` in the Telegram error handler and treating it as a network error (incrementing the retry counter instead of logging it as an "Unhandled Error" with traceback).

## Manual Verification Steps in Telegram

1. **Setup Profile with Variants**:
   - Send `/setcourses`.
   - Choose "➕ Semester hinzufügen".
   - Select Faculty (e.g., Maschinenbau).
   - Select Degree & Semester (e.g., MABB.3).
   - **Expect**: Bot should show "Für MABB.3 wurden verschiedene Gruppen gefunden. Welcher Gruppe gehörst du an?" with buttons for .E, .Z, etc.
   - Choose a group.
   - **Expect**: "✅ Kurs `MABB.3.E` hinzugefügt."

2. **Test Vague Personal Query**:
   - Ask: "Was habe ich heute?"
   - **Expect**: Timetable for the stored course is shown directly without the bot asking "Welchen Kurs meinst du?".

3. **Test Module Search in Profile**:
   - Ask: "Wann habe ich Thermodynamik?"
   - **Expect**: Bot searches stored profile courses and returns results (or "Keine Einträge" without CONFIRM_SENTINEL).

4. **Test "Next Week" Range**:
   - Ask: "Was habe ich nächste Woche?"
   - **Expect**: Results for the Monday-Friday range of the following week.
