# Issue: Next Occurrence Feature with Cancellation & Revalidation

## Problem
Users asking "Wann habe ich <Modul>?" should get the next valid (non-cancelled) occurrence. 
The system should ensure the data is fresh, especially if the event is soon.

## Solution
Implemented `get_next_occurrence` tool in `src/tools.py` with the following logic:
1.  **Caching**: Uses `user_plan_cache` from `db.py`.
2.  **Cancellation Detection**: Updated `_parse_ical` to detect "fällt aus", "entfällt", etc.
3.  **Revalidation**: 
    - If candidate is within 24h (configurable via `REVALIDATE_IF_EVENT_WITHIN_HOURS`), a refetch is triggered.
    - If cache is stale or missing, a refetch is triggered.
4.  **Routing**: Updated `src/router.py` and `src/agent.py` to route "Wann habe ich..." to the new tool.
5.  **Presentation**: Added `_fmt_next_occurrence` in `src/formatter.py`.

## Configuration
Added `revalidate_if_event_within_hours` (default: 24) to `src/config.py`.

## Verification
- Added `tests/test_next_occurrence.py` covering:
    - Successful fetch from cache (future event).
    - Skipping cancelled events in cache.
    - Triggering refetch for soon-to-happen events.
    - Handling no upcoming events found.
- Verified with `uv run pytest tests/test_next_occurrence.py` (5/5 PASSED).

## Next Steps
- Monitor logs for "Revalidiere Cache" and "Überspringe abgesagtes Event".
- Consider extending this to other "personal" queries if needed.
