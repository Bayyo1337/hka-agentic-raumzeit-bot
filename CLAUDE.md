# CLAUDE.md – raumzeit-ki-agent

Telegram bot that translates natural language into Raumzeit HKA API calls and formats the results. The LLM only selects tools and parameters — all formatting is done in Python.

## Run & Lint

```bash
make run      # uv sync + python -m src.bot
make lint     # ruff check
```

## Architecture

```
src/
  bot.py        # Telegram handlers, rate limiting, 3-stage course escalation
  agent.py      # LiteLLM tool-use loop (tool_choice="required" → "auto")
  tools.py      # Raumzeit API wrapper + tool definitions (OpenAI format)
  formatter.py  # Python formatter: tool results → Telegram Markdown text
  db.py         # SQLite (aiosqlite): rate limits, token tracking, chat history, course index
  config.py     # Pydantic Settings from .env
```

**Data flow:** User message → `bot.py` → `agent.run()` → LiteLLM → tool calls → `tools.py` → `formatter.format_results()` → Telegram reply

**Key invariant:** The LLM never generates the reply text. `formatter.py` owns all presentation logic.

## Environment (.env)

```
TELEGRAM_BOT_TOKEN=
RAUMZEIT_LOGIN=
RAUMZEIT_PASSWORD=
LLM_PROVIDER=groq           # claude | gemini | groq | mistral | openrouter
GROQ_API_KEY=               # only the chosen provider's key is needed
ALLOWED_USER_IDS=           # comma-separated Telegram IDs; empty = open (dev only)
ADMIN_USER_IDS=
RATE_LIMIT_PER_HOUR=20      # 0 = no limit
MAX_TOKENS_PER_USER=0       # 0 = no limit
LOG_LEVEL=INFO
```

## Key Design Decisions

- **`MAX_TOOL_CALLS = 6`** (agent.py) — hard cap to prevent LLM from iterating day-by-day through a semester (was 422k tokens on one query)
- **Course index** (SQLite `course_index` table) — Raumzeit has no listing endpoint for valid course-group combos. The bot probes A–Z + known multi-char suffixes (DF, U61, …) and caches results. Rebuilt on startup if stale (>7 days) or via `/sync`.
- **iCal TZID parsing** — Raumzeit iCal uses `DTSTART;TZID=Europe/Berlin:20260410T113000`. Split on last `:` not first to avoid `Europe/Berlin:...` being treated as the value.
- **3-stage course escalation** when `get_course_timetable` returns 0 entries:
  1. Ask user "Stimmt das so? (ja/nein)"
  2. On "nein": brute-force all suffixes via `fetch_course_brute_force()`
  3. Still empty: ask user for exact Raumzeit key (e.g. `MABB.6.DF`)
  4. Still empty: save feedback log to `data/feedback/YYYY-MM-DD_{chat_id}.json`
- **Deduplication** in `formatter._dedup_bookings()` — same room can appear in multiple course group iCal feeds; deduplicate by `(start, end, name)` before formatting.

## Database (data/bot.db)

| Table | Purpose |
|---|---|
| `requests` | Rate limiting — timestamp per user, cleaned up after 2h |
| `tokens` | Cumulative input/output token counts per user |
| `histories` | Last 3 conversation exchanges per chat (JSON) |
| `course_index` | Known valid course keys: `MABB.7`, `MABB.7.A`, `MABB.6.DF`, … |

## Raumzeit API

- Auth: `POST /private/api/v1/authentication` → Bearer JWT (cached in memory)
- Room timetable: `GET /private/api/v1/timetable/room/{room}?date=YYYY-MM-DD`
- Course timetable: iCal at `/public/api/v1/ical/course/{KÜRZEL.SEMESTER}` — response is Raumzeit's own text format: `weekday#start_min#end_min#course_id#name`
- Lecturer timetable: `GET /private/api/v1/timetable/lecturer/{account_kürzel}`
- No endpoint exists to list valid course-group combinations → brute-force probing

## Bot Commands

User: `/start`, `/stats`, `/reset`  
Admin: + `/rooms`, `/admin`, `/sync`
