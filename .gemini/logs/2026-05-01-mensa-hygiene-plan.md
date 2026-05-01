# Mensa Date Determinism & History Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Mensa date resolution errors, prevent meal ID hallucinations, and clean up LLM prompts through intent-aware history filtering.

**Architecture:** 
1. **History Hygiene:** Filter history turns in `agent.py` based on the determined intent.
2. **Deterministic Weekday Resolution:** Add a Python helper to map German weekdays to dates and override LLM extracted dates in `agent.py`.
3. **Mensa Tool Fixes:** Update `tools.py` to extract dates from meal IDs for correct cache warming and implement a date-aware category lookup.

**Tech Stack:** Python, LiteLLM, Pytest

---

### Task 1: Weekday Resolution Helper

**Files:**
- Modify: `src/agent.py`
- Test: `tests/test_mensa_hygiene.py`

- [ ] **Step 1: Write tests for weekday resolution**

```python
from datetime import date, timedelta
from src.agent import resolve_german_weekday

def test_resolve_german_weekday():
    ref = date(2026, 5, 1) # Friday
    # Montag should be 2026-05-04
    assert resolve_german_weekday("Was gibt es am Montag?", ref) == date(2026, 5, 4)
    # Freitag should be today (2026-05-01)
    assert resolve_german_weekday("Heute ist Freitag", ref) == date(2026, 5, 1)
    # Unknown should return None
    assert resolve_german_weekday("Irgendwann", ref) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mensa_hygiene.py -k resolve_german_weekday`
Expected: FAIL (ImportError or AttributeError)

- [ ] **Step 3: Implement `resolve_german_weekday` in `src/agent.py`**

```python
import re

def resolve_german_weekday(text: str, ref_date: date) -> date | None:
    weekdays = {
        "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3,
        "freitag": 4, "samstag": 5, "sonntag": 6
    }
    text_lower = text.lower()
    for name, day_idx in weekdays.items():
        if name in text_lower:
            days_ahead = day_idx - ref_date.weekday()
            if days_ahead < 0:
                days_ahead += 7
            return ref_date + timedelta(days=days_ahead)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mensa_hygiene.py -k resolve_german_weekday`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent.py tests/test_mensa_hygiene.py
git commit -m "feat: add deterministic weekday resolution helper"
```

---

### Task 2: History Hygiene Implementation

**Files:**
- Modify: `src/agent.py`
- Test: `tests/test_mensa_hygiene.py`

- [ ] **Step 1: Write test for history filtering**

```python
from src.agent import filter_history_by_intent

def test_filter_history_by_intent():
    history = [
        {"role": "user", "content": "Wann habe ich Thermodynamik?"},
        {"role": "assistant", "content": "📅 Dein Stundenplan... M-102"},
        {"role": "user", "content": "Was gibt es in der Mensa?"},
        {"role": "assistant", "content": "Mensa Moltke: Schnitzel"}
    ]
    
    # Mensa intent should strip timetable turns
    mensa_filtered = filter_history_by_intent(history, "mensa_menu")
    assert len(mensa_filtered) == 2
    assert "Thermodynamik" not in mensa_filtered[0]["content"]
    
    # Timetable intent should strip mensa turns
    timetable_filtered = filter_history_by_intent(history, "course_timetable")
    assert len(timetable_filtered) == 2
    assert "Schnitzel" not in timetable_filtered[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mensa_hygiene.py -k filter_history_by_intent`
Expected: FAIL

- [ ] **Step 3: Implement `filter_history_by_intent` in `src/agent.py`**

```python
def filter_history_by_intent(history: list[dict], intent: str) -> list[dict]:
    timetable_keywords = ["raum", "kurs", "dozent", "stundenplan", "plan", "m-102", "thermodynamik", "vorlesung"]
    mensa_keywords = ["mensa", "speiseplan", "essen", "hunger", "allergene", "gericht", "schnitzel", "wahlessen"]
    
    filtered = []
    if intent in ["mensa_menu", "mensa_details"]:
        for msg in history:
            content_lower = msg["content"].lower()
            if not any(kw in content_lower for kw in timetable_keywords):
                filtered.append(msg)
    elif intent in ["course_timetable", "room_timetable", "lecturer_timetable", "next_occurrence"]:
        for msg in history:
            content_lower = msg["content"].lower()
            if not any(kw in content_lower for kw in mensa_keywords):
                filtered.append(msg)
    else:
        filtered = history
        
    return filtered
```

- [ ] **Step 4: Update `run` function in `src/agent.py` to use filtering**

```python
# Inside run() before processed_history is built:
    filtered_history = filter_history_by_intent(history, intent)
    processed_history = []
    for msg in filtered_history:
        # ... existing content truncation ...
```

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_mensa_hygiene.py`
Expected: PASS

---

### Task 3: Weekday Override & Prompt Refinement

**Files:**
- Modify: `src/agent.py`

- [ ] **Step 1: Update `_extraction_prompt` to include day mapping**

```python
# Inside _extraction_prompt
    today = date.today()
    days_info = []
    for i in range(7):
        d = today + timedelta(days=i)
        days_info.append(f"{d.strftime('%A')}: {d.isoformat()}")
    
    sections.append("\nAktuelle Wochentage:\n" + "\n".join(days_info))
```

- [ ] **Step 2: Update `run` to apply weekday override**

```python
# After parsing 'calls':
    for call in calls:
        if call.get("tool") in ["get_mensa_menu", "get_mensa_meal_details"]:
            resolved_date = resolve_german_weekday(user_message, date.today())
            if resolved_date:
                if "args" not in call: call["args"] = {}
                call["args"]["date"] = resolved_date.isoformat()
                log.debug("Override date to %s due to weekday in message", resolved_date.isoformat())
```

- [ ] **Step 3: Commit**

```bash
git add src/agent.py
git commit -m "feat: apply deterministic weekday overrides and prompt day mapping"
```

---

### Task 4: Mensa Tool Date-Aware Warming & Category Fix

**Files:**
- Modify: `src/tools.py`

- [ ] **Step 1: Fix date-aware warming in `get_mensa_meal_details`**

```python
# Modify src/tools.py: get_mensa_meal_details
# Extract date from meal_id if it follows a pattern or use current context
async def get_mensa_meal_details(meal_id: str, date_str: str | None = None, is_retry: bool = False) -> dict:
    # ...
    if not is_retry:
        target_date = date_str or date.today().isoformat()
        # Parse date from meal_id if it ends with YYYY-MM-DD
        match = re.search(r'(\d{4}-\d{2}-\d{2})$', meal_id)
        if match:
            target_date = match.group(1)
            
        if not await db.get_mensa_meals_for_day(target_date):
            await get_mensa_menu(date=target_date)
            return await get_mensa_meal_details(meal_id, date_str=target_date, is_retry=True)
```

- [ ] **Step 2: Update `TOOL_HANDLERS` for `get_mensa_meal_details`**

```python
"get_mensa_meal_details": lambda inp: get_mensa_meal_details(inp.get("meal_id"), inp.get("date")),
```

- [ ] **Step 3: Commit**

```bash
git add src/tools.py
git commit -m "fix: date-aware cache warming for mensa details"
```

---

### Task 5: Verification & Cleanup

- [ ] **Step 1: Final Manual Verification**

- Query: "Was gibt es am Montag?" -> Check log for correct date override.
- Query: "Allergene im Wahlessen 1 am Mittwoch" -> Check if tool resolves correct date.

- [ ] **Step 2: Cleanup temporary tests**

```bash
rm tests/test_mensa_hygiene.py
```

- [ ] **Step 3: Final Commit**

```bash
git commit -m "chore: cleanup and final verification of mensa fixes"
```
