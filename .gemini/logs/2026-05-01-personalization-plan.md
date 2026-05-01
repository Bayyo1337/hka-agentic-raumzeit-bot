# Personalization Workflow Fix & Mensa Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the personalization workflow by making the router profile-aware, refining agent extraction rules, and improving empty-result UX, while also adding observability for Mensa API calls.

**Architecture:** Profile-Aware Router (LLM gets user course config), Agent-based extraction with strict Personal vs Explicit rules, and Formatter-side UX cleanup.

**Tech Stack:** Python, litellm, aiosqlite, httpx, pytest.

---

### Task 1: Test Foundation (Personalization)

**Files:**
- Create: `tests/test_personalization.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from src.router import Router
from src.agent import _extraction_prompt

@pytest.mark.asyncio
async def test_router_avoids_clarification_with_profile():
    router = Router()
    user_context = {"user_id": 123, "primary_course": "[MABB.2]"}
    # Simulated personal query
    result = await router.classify_message("Was habe ich heute?", user_context, {})
    # This might fail initially if router doesn't use primary_course
    assert result.strategy.action == "agent_flow"

def test_agent_extraction_prompt_contains_profile():
    prompt = _extraction_prompt(primary_course="[MABB.2]", intent="course_timetable")
    assert "MABB.2" in prompt
    assert "SEINEN persönlichen Plan" in prompt
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_personalization.py -v`
Expected: FAIL (Router might return ask_clarification or action might be wrong)

- [ ] **Step 3: Commit baseline**

```bash
git add tests/test_personalization.py
git commit -m "test: add personalization baseline tests"
```

---

### Task 2: Profile-Aware Router

**Files:**
- Modify: `src/router.py`
- Modify: `src/bot.py`

- [ ] **Step 1: Update Router `classify_message` and prompt**

```python
# src/router.py

# Update _llm_fallback prompt to include profile context
async def _llm_fallback(self, text: str, primary_course: str | None = None) -> RouterOutput:
    profile_info = f"\nNutzer-Profil: {primary_course}" if primary_course else "\nNutzer-Profil: Kein Kurs hinterlegt."
    prompt = f"""... (existing) ...
Nachricht: "{text}"
{profile_info}

Regel: Wenn der Nutzer nach SEINEM Plan fragt (ich, mein, heute, morgen, wann habe ich) und ein Kurs im Profil steht, nutze IMMER agent_flow.
Frage nur nach Klärung (ask_clarification), wenn der Intent klar ist, aber KEIN Kurs im Text UND das Profil leer ist.
"""
    # ... update litellm call to pass this prompt ...
```

- [ ] **Step 2: Update `classify_message` signature and calls**

```python
# src/router.py
async def classify_message(self, text: str, user_context: dict, state: dict) -> RouterOutput:
    primary_course = user_context.get("primary_course")
    # ... pass to _llm_fallback ...
```

- [ ] **Step 3: Update `src/bot.py` to pass the profile**

```python
# src/bot.py handle_message
u = await db.get_user(user_id)
primary_course = u.get("primary_course") if u else None
# ...
router_result = await router_instance.classify_message(
    text, 
    {"user_id": user_id, "chat_id": chat_id, "primary_course": primary_course}, 
    u or {}
)
```

- [ ] **Step 4: Verify with Task 1 tests**

Run: `pytest tests/test_personalization.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/router.py src/bot.py
git commit -m "feat: make router profile-aware to avoid unnecessary clarification"
```

---

### Task 3: Agent Logic Refinement

**Files:**
- Modify: `src/agent.py`

- [ ] **Step 1: Refine `_extraction_prompt` instructions**

```python
# src/agent.py
def _extraction_prompt(primary_course: Optional[str] = None, intent: str = "smalltalk_fallback") -> str:
    # ...
    if intent in ["course_timetable", "smalltalk_fallback"]:
        sections.append(f"""
Fehler-Handling & Priorisierung:
1. PERSÖNLICHE ANFRAGE: Wenn der Nutzer nach SEINEM Plan fragt ("mein Plan", "was habe ich heute", "wann habe ich..."), MUSST du die Kurse aus dem 'Nutzer-Profil' ({primary_course}) verwenden. Erzeuge für JEDEN Kurs einen `get_course_timetable` Call.
2. EXPLIZITE ANFRAGE: Wenn der Nutzer einen konkreten Kurs-Key nennt (z.B. "MABB.2", "Maschinenbau Sem 3"), ignoriere das Profil und führe den Call nur für diesen Key aus.
3. KEIN PROFIL: Wenn es eine persönliche Anfrage ist, aber das Profil 'Kein Kurs hinterlegt' zeigt, gib {{"error": "no_course"}} zurück.""")
```

- [ ] **Step 2: Update `run` to ensure history doesn't confuse the LLM**

Ensure `primary_course` is always current from DB.

- [ ] **Step 3: Commit**

```bash
git add src/agent.py
git commit -m "feat: refine agent extraction rules for personalization"
```

---

### Task 4: Formatter & Bot UX Fixes

**Files:**
- Modify: `src/formatter.py`
- Modify: `src/bot.py`

- [ ] **Step 1: Update `format_results` to handle `is_personal` flag**

```python
# src/formatter.py
def format_results(collected: list[tuple[str, dict]], user_message: str, user_config: list[dict] = None, is_personal: bool = False) -> str:
    # ...
    if len(course_calls) > 1 or (len(course_calls) == 1 and user_config):
        # ...
        if not all_bookings:
            msg = "📅 *Dein Stundenplan*\nKeine Belegungen gefunden."
            if not is_personal:
                msg += "\n\n" + CONFIRM_SENTINEL
            return msg
```

- [ ] **Step 2: Update `src/bot.py` to set `is_personal`**

```python
# src/bot.py handle_message
# Heuristik: Ist es eine persönliche Anfrage?
is_personal = any(kw in text.lower() for kw in ["mein", "ich", "heute", "morgen", "nächste woche"]) and primary_course is not None

# ...
reply = formatter.format_results(collected_results, text, user_config=config, is_personal=is_personal)
```

- [ ] **Step 3: Commit**

```bash
git add src/formatter.py src/bot.py
git commit -m "fix: improve UX for empty personal plans"
```

---

### Task 5: Mensa Observability

**Files:**
- Modify: `src/tools.py`

- [ ] **Step 1: Add timing and logging to Mensa tools**

```python
# src/tools.py
async def get_mensa_menu(canteen: str | None = None, date: str | None = None) -> dict:
    start_t = time.monotonic()
    log.info("Mensa-API: Rufe Speiseplan ab (canteen=%s, date=%s)", canteen, date)
    # ... after fetch ...
    elapsed = time.monotonic() - start_t
    log.info("Mensa-API: Speiseplan erhalten in %.2fs (%d Gerichte)", elapsed, len(flattened_meals))
    # ... on error ...
    log.error("Mensa-API Fehler: %s", e)
```

- [ ] **Step 2: Commit**

```bash
git add src/tools.py
git commit -m "feat: add observability logging for Mensa API"
```

---

### Task 6: Date Logic Standardisation ("Nächste Woche")

**Files:**
- Modify: `src/tools.py`

- [ ] **Step 1: Standardise `_current_week_range` and handle next week logic**

```python
# src/tools.py
def _next_week_range() -> tuple[str, str]:
    """Gibt Mo–Fr der NÄCHSTEN Kalenderwoche zurück."""
    today = _date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    next_friday = next_monday + timedelta(days=4)
    return next_monday.isoformat(), next_friday.isoformat()
```

- [ ] **Step 2: Update `get_course_timetable` to support date range directly if passed from Agent**

- [ ] **Step 3: Commit**

```bash
git add src/tools.py
git commit -m "fix: standardise 'nächste Woche' date range calculation"
```
