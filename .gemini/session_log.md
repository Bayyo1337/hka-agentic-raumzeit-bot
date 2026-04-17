
# Session Log - 17.04.2026

## Task: Fix "Message is too long" Bug
Telegram has a character limit of 4096 per message. Some responses (e.g., large conflict reports) exceeded this.

### Changes
- **src/bot.py**:
    - Updated `_send_reply` to detect messages longer than 4000 characters.
    - Implemented a splitting logic that breaks the message into chunks, preferably at line breaks.
    - Added a suffix `(1/n)` to chunks if there are multiple parts.
    - Ensured all part-messages are tracked in `_bot_messages` for later deletion via `/clear`.

### Validation
- **Syntax**: `uv run python -m py_compile src/bot.py` - PASSED
- **Logic**: Ran `scripts/repro_issue.py` with a 10,000 character mock message.
    - Successfully split into 3 chunks.
    - Each chunk was within the Telegram limit.
- **Linting**: Ruff reported existing style issues (E701, E722), but they are unrelated to my change and reflect the current state of the codebase. I chose not to refactor the entire file to maintain surgicality, as per mandates.

### Dependencies
- No new dependencies.
