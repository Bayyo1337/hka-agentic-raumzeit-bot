# Spec: Full GDPR/DSGVO Compliance Harmonization

**Date:** 2026-05-01
**Status:** Approved
**Topic:** Resolving contradictions in privacy policy, implementing structured feedback management, and granular consent for error reporting.

## 1. Problem Statement
The current implementation has several GDPR-related gaps:
1. **Misleading Info:** `src/privacy.py` claims encryption and server location which are unverified/unmanaged by code.
2. **Global Retention:** `run_gdpr_cleanup` uses hardcoded values instead of per-user settings for telemetry and feedback.
3. **Inconsistent Feedback:** Bug/Issue reports are stored as Markdown, making them hard to include in Export/Delete routines.
4. **Privacy Leakage:** `_error_handler` sends raw user input to admins and logs without checking for consent or applying PII redaction.

## 2. Goals
- Harmonize all privacy texts and documentation.
- Implement granular consent for error reporting (`allow_error_reports`).
- Transition feedback/issue logs to a structured JSON format in `data/feedback/`.
- Ensure all user data (including feedback) is fully included in GDPR Export and Delete actions.
- Enforce per-user TTL (Retention) for all data types.

## 3. Design Details

### 3.1 Data Architecture (Feedback & Issues)
- **Migration:** Move from `issues/active/*.md` to `data/feedback/*.json`.
- **Format:** JSON with mandatory `user_id`, `timestamp` (DD.MM.YYYY HH:MM:SS), and `type` fields.
- **Handling:** Admin commands (`/feedback`, `/delfeedback`) will be updated to parse these JSON files.

### 3.2 Privacy & Consent
- **New Setting:** `allow_error_reports` (Default: 0/Off).
- **Error Handler Logic:**
    - Always apply `agent.redact_pii()` to `user_input`.
    - If `allow_error_reports` is OFF: Set `user_id` to `0`, replace `user_input` with `[REDACTED]`, and send only technical trace to admins.
    - If `allow_error_reports` is ON: Store full (redacted) report linked to `user_id`.

### 3.3 Database & Cleanup
- Update `user_privacy_settings` table to include `allow_error_reports`.
- Update `run_gdpr_cleanup` to:
    - Join with `user_privacy_settings` to get individual `telemetry_ttl_hours`.
    - Use `feedback_ttl_days` to clean up files in `data/feedback/`.

### 3.4 Text Harmonization
- **`src/privacy.py`**: Remove unverified claims about encryption/location. Use: "Protected SQLite databases on a private server."
- **`docs/DSGVO.md`**: Update data inventory to include `data/feedback/`, the new setting, and clarified retention periods.

## 4. Testing Strategy
- **Unit Tests (`tests/test_privacy.py`):**
    - Verify `allow_error_reports` impacts file creation in `data/feedback/`.
    - Verify Export includes JSON feedback files.
    - Verify Delete removes JSON feedback files.
    - Verify `run_gdpr_cleanup` respects per-user TTL for telemetry and feedback.

## 5. Constraints
- No new dependencies.
- Maintain existing Python compile and lint/test targets.
