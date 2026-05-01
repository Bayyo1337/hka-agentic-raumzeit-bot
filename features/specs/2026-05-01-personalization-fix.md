# Spec: Personalization Workflow Fix & Mensa Observability

**Date:** 2026-05-01
**Status:** Approved
**Branch:** `gemini`

## 1. Problem Description
- Users experience "zu vage" (too vague) errors from the router even when they have a saved course profile.
- Personal schedule queries like "Was habe ich heute?" often result in "Keine Belegungen gefunden" or unnecessary "Stimmt das so?" (confirmation) prompts.
- Mensa queries have unspecified issues, and there is a lack of logging to diagnose them.
- "Nächste Woche" (next week) queries are inconsistent in their date range.

## 2. Goals
- Ensure personal schedule queries use the stored profile by default without asking for clarification.
- Differentiate between personal queries (use profile) and explicit course queries (use provided key).
- Improve UX for empty personal schedules (no more "Stimmt das so?" if free).
- Add robust logging for Mensa API interactions.
- Standardize "Nächste Woche" to Mo-Fr of the next calendar week.

## 3. Architecture & Components

### 3.1 Router Overhaul (`src/router.py`)
- **Action:** Update `classify_message` to accept `primary_course`.
- **Logic:** The LLM router prompt will include the user's saved course(s).
- **Rule:** If the user has a profile and asks a personal question (e.g., "was habe ich"), the router must return `agent_flow` for `course_timetable` or `conflict_analysis`, never `ask_clarification`.

### 3.2 Agent Intelligence (`src/agent.py`)
- **Extraction Prompt:** 
  - Explicitly define "Personal Query" vs "Explicit Query".
  - Rule: For personal queries, generate one `get_course_timetable` call for *each* course in the profile.
  - Rule: If a specific course key is mentioned in the message, ignore the profile and query that key only.
- **Max Calls:** Ensure the 6-call limit is respected even for multi-course profiles.

### 3.3 Formatter & Bot UX (`src/formatter.py`, `src/bot.py`)
- **Filtering:** `formatter.format_results` will continue to filter results based on the user's excluded groups/modules.
- **Empty Results:** 
  - If a query is identified as "personal" and returns zero bookings, the formatter will return a clean "You have no lectures today" message.
  - The `CONFIRM_SENTINEL` ("Stimmt das so?") will be OMITTED for personal queries to avoid the "vage" loop.
- **Date Resolution:** "Nächste Woche" will be calculated as Monday to Friday of the next ISO week.

### 3.4 Mensa Observability (`src/tools.py`)
- **Logging:** 
  - Log `INFO` before and after Mensa API calls with `canteen_id`, `date`, and `elapsed_time`.
  - Log `WARNING` or `ERROR` for all Mensa API failures with full response body if possible (masking tokens).
- **Documentation:** Create `docs/mensa_debug.md` with common queries and expected behavior.

## 4. Implementation Details

### 4.1 Router Prompt Update
```
Nutzer-Profil: [MABB.2, INFB.4]
Regel: Wenn der Nutzer nach SEINEM Plan fragt (ich, mein, heute) und das Profil nicht leer ist, nutze 'agent_flow'.
```

### 4.2 Bot Logic Change
```python
# src/bot.py
u = await db.get_user(user_id)
primary_course = u.get("primary_course")
# Pass to router
router_result = await router_instance.classify_message(text, {"user_id": user_id, "primary_course": primary_course}, u or {})
```

## 5. Testing Strategy
- **Unit Tests**:
  - Test router decision logic with/without profile.
  - Test agent extraction for personal vs explicit queries.
  - Test date calculation for "nächste Woche" on various days of the week.
- **Manual Verification**:
  1. Run `/setcourses` to add a course.
  2. Ask "Was habe ich heute?" -> Verify no clarification is asked.
  3. Ask "Stundenplan INFB.2" -> Verify profile is ignored.
  4. Ask "Nächste Woche" -> Verify 5 tool calls for the next Mon-Fri.

## 6. Mensa Debug Checklist (`docs/mensa_debug.md`)
- [ ] Query: "Was gibt es heute in der Mensa?" -> Check logs for `get_mensa_menu` timing.
- [ ] Query: "Allergene im Seelachs" -> Check `get_mensa_meal_details` for successful ID lookup.
- [ ] Check `data/cache.db` for `mensa_meals` entries.
