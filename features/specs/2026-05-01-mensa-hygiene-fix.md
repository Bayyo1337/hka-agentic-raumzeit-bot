# Spec: Mensa Date Determinism & History Hygiene

## 1. Problem Definition
Current Mensa-related intent handling suffers from:
- **Non-deterministic date resolution:** LLM hallucinating YYYY-MM-DD for German weekdays.
- **Cache Warming mismatch:** `get_mensa_meal_details` warms the cache for "today" instead of the queried date.
- **Prompt Contamination:** Unrelated timetable context in Mensa prompts increases tokens and hallucination risk.
- **Hallucinated meal_ids:** LLM inventing meal IDs instead of using UUIDs or names.

## 2. Proposed Changes

### A. Deterministic Weekday Resolution (`src/agent.py`)
- Implement `resolve_german_weekday(text: str, ref_date: date) -> date | None`.
- Maps "Montag" through "Sonntag" to the next occurrence relative to `ref_date`.
- In `agent.run()`:
    - Post-process LLM output.
    - If a weekday is found in `user_message`, override any `date` argument in Mensa tool calls with the resolved date.

### B. History Hygiene (`src/agent.py`)
- Implement `filter_history_by_intent(history: list[dict], intent: str) -> list[dict]`.
- For `mensa_menu` and `mensa_details`:
    - Remove all turns containing keywords: "Raum", "Kurs", "Dozent", "Stundenplan", "Plan", "M-102", etc.
    - Keep only Mensa-related turns or simple smalltalk.
- For timetable intents:
    - Remove Mensa menu responses (which are large and irrelevant).
- Add logging to track filtered entries.

### C. Mensa Tool Enhancements (`src/tools.py`)
- **`get_mensa_meal_details` Update:**
    - Parse date from `meal_id` if encoded (e.g., UUID-YYYY-MM-DD pattern).
    - If cache is empty, call `get_mensa_menu` for the *extracted date*, not `today`.
- **Deterministic Category Resolution:**
    - Improve the "Line/Category" fallback to be date-aware.
    - If a user asks for "Wahlessen 1 am Mittwoch", ensure it looks up Wednesday's cache.

### D. Prompt Refinement (`src/agent.py`)
- Update `_extraction_prompt` for Mensa intents to:
    - Include a mapping of the next 7 days (e.g., "Heute: Freitag, 2026-05-01, Montag: 2026-05-04").
    - Explicitly forbid inventing meal IDs.

## 3. Architecture & Interfaces

### New Internal Helper in `agent.py`
```python
def resolve_german_weekday(text: str, ref_date: date) -> date | None:
    # Logic to find "montag", "dienstag", etc. and return next date
```

### Updated `run` logic in `agent.py`
```python
async def run(...):
    # 1. Router determines intent
    # 2. Filter history
    # 3. Call LLM
    # 4. Apply overrides (Weekday resolution)
    # 5. Execute tools
```

## 4. Verification Plan

### Automated Tests (`tests/test_mensa_fixes.py`)
- `test_weekday_mapping`: Verify "Montag" resolves to 2026-05-04 if today is 2026-05-01.
- `test_history_hygiene`: Verify mixed history is correctly stripped based on intent.
- `test_meal_detail_warming`: Mock empty cache and verify `get_mensa_menu` is called with the correct date extracted from a query or ID.

### Manual Verification
- Message: "Was gibt es am Montag?" -> Verify it queries 2026-05-04.
- Message: "Allergene im Wahlessen 1 am Mittwoch" -> Verify it finds allergens for Wednesday's meal even if ID is fabricated.
