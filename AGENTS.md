# Agent instructions

This file is the entry point for AI agents working in this repository. Read it
before changing code. More detailed role guidance lives in `.agents/`.

## Project

This is an asynchronous Python Telegram bot for HKA Raumzeit. It translates
natural-language requests into deterministic API tool calls and formats all
user-facing output in Python.

The main runtime path is:

`src/bot.py` → `src/router.py` / `src/agent.py` → `src/tools.py` → `src/formatter.py`

Keep the LLM responsible for intent and tool parameters only. It must not
generate the final Telegram response.

## Required workflow

1. Read the relevant code, tests, and `docs/AGENTS.md` before editing.
2. For a bug, reproduce the behavior before changing it whenever practical.
3. Make the smallest complete change and update directly related tests or docs.
4. Run syntax validation for every changed Python file:
   `uv run python -m py_compile <files>`
5. Run the narrowest relevant tests, then `make lint` when the change is
   complete.
6. Report changed files, validation commands, and any remaining limitation.

## Repository invariants

- Keep API access in `src/tools.py`, presentation logic in `src/formatter.py`,
  and Telegram orchestration in `src/bot.py`.
- Preserve asynchronous I/O and existing error-reporting behavior.
- Normalize event names before comparisons or deduplication with
  `re.sub(r'[^a-z0-9]', '', value.lower())`.
- Never read, print, or commit secrets from `.env`.
- Never commit runtime data such as `data/*.db`, logs, or generated test runs.
- Do not perform destructive Git operations or rewrite unrelated work.

## Agent roles

Use the role that matches the current phase:

- `.agents/roles/strategist.md` — scope and sequence work.
- `.agents/roles/researcher.md` — inspect code and produce evidence.
- `.agents/roles/implementer.md` — make and validate code changes.
- `.agents/roles/reviewer.md` — review the diff and run final checks.

The reusable handoff format is in `.agents/templates/handoff.md`. Existing
Gemini CLI skills under `.gemini/skills/` remain supported and may be used by
Gemini-specific workflows.
