# Spec: GDPR Opt-In Onboarding & Menu Harmonization

**Date:** 2026-05-01
**Status:** Approved
**Topic:** Implementing a strict Opt-In flow for new users, seamless message resumption, and updating Telegram Auto-Complete menus.

## 1. Problem Statement
- **Compliance Risk:** The bot currently processes natural language queries and stores user profiles by default (Opt-Out). Strict GDPR compliance requires explicit Opt-In before sending data to third-party AI APIs.
- **UX Friction:** If an Opt-In blocks a user's first query (e.g., "Where is M-102?"), forcing them to retype it after consenting is a poor user experience.
- **Menu Gaps:** Several newly added commands (like `/retention` and numerous admin commands) are missing from the Telegram Auto-Complete menus (`_USER_COMMANDS`, `_ADMIN_COMMANDS`), making them hard to discover.

## 2. Goals
- Implement a strict, database-backed Opt-In gatekeeper (`has_consented`).
- Ensure the user's initial blocked message is temporarily saved and automatically processed upon consent (seamless UX).
- Update `/start` and `/help` texts to prominently feature privacy controls.
- Synchronize all implemented handlers with the Telegram Auto-Complete command list.

## 3. Design Details

### 3.1 Database Changes (`src/db.py`)
- Add `has_consented` (INTEGER, default 0) to the `users` table.
- Add `pending_message` (TEXT, default '') to the `users` table.
- Provide helper methods: `get_consent_status(user_id)`, `set_consent_status(user_id, status)`, `save_pending_message(user_id, msg)`, `get_and_clear_pending_message(user_id)`.

### 3.2 The Gatekeeper (`src/bot.py`)
- In `handle_message`, immediately after `upsert_user`:
  - Check `has_consented`.
  - If `0`: Save the user's text to `pending_message`.
  - Send the Opt-In text: Explain what is stored (Profile, History) and where it goes (AI APIs).
  - Provide an InlineKeyboardMarkup with `[✅ Ich stimme zu]` (callback: `privacy_opt_in`) and `[📄 Details lesen (/privacy)]`.
  - `return` (block further processing).

### 3.3 Seamless Resumption (`src/bot.py`)
- In the callback handler for `privacy_opt_in`:
  - Set `has_consented` to `1`.
  - Fetch the `pending_message`.
  - Edit the prompt message to: "✅ Danke für deine Zustimmung! Ich verarbeite nun deine erste Anfrage..."
  - If `pending_message` exists, manually trigger the agent processing logic (or refactor `handle_message` slightly to allow calling the inner processing logic directly with the pending text).

### 3.4 Menu and Help Updates (`src/bot.py`)
- **Help Text:** Add a dedicated "🔒 Datenschutz & DSGVO" section listing `/privacy`, `/consent`, `/data`, `/export`, `/delete`, `/retention`.
- **Start Text:** Add a bullet point to "Erste Schritte" advising users they can manage their privacy via `/consent`.
- **Auto-Complete Lists (`_USER_COMMANDS`, `_ADMIN_COMMANDS`):**
  - Add `/retention` to `_USER_COMMANDS`.
  - Add `/rooms`, `/ping`, `/indexage`, `/courses`, `/feedback`, `/delfeedback`, `/user`, `/ban`, `/unban`, `/resetlimit`, `/setlimit`, `/cleartokens`, `/clearhistory`, `/setprovider` to `_ADMIN_COMMANDS` with concise descriptions.

## 4. Testing Strategy
- Unit test the database schema changes and helpers in `tests/test_db.py` or similar.
- Integration test (manual or via mock) the Opt-In flow: First message is blocked -> Consent clicked -> First message is processed.

## 5. Constraints
- No new dependencies.
- Ensure backwards compatibility with existing users (we will need a migration strategy. For existing users who already have history/tokens, we should ideally grandfather them in by setting `has_consented=1` during migration, OR force them to consent on their next message. We will choose to **force consent on their next message** to be strictly compliant, so the migration sets `has_consented=0` for everyone, or relies on the default 0).
