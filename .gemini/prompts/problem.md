# Problem: Regression in src/db.py und instabile Admin-Benachrichtigungen

## Hintergrund & Motivation
Nach dem Datenbank-Refactoring (Säulen-Modell) sind Funktionen verloren gegangen, was zu Abstürzen führt. Zudem schlagen Admin-Benachrichtigungen bei Sonderzeichen im Fehler-Traceback fehl (Markdown-Parsing-Fehler). Nutzer wünschen zudem aussagekräftigere Dateinamen für Fehlerberichte.

## Ursachenanalyse / Ist-Zustand
1. **Fehlende Funktion:** `src.db.get_custom_rate_limit` wurde beim Refactoring entfernt, wird aber vom Bot/Admin-Modul benötigt.
2. **Markdown-Fehler:** In `src/bot.py:_error_handler` werden `user_info`, `user_input` und `error_msg` ohne Escaping in einen Markdown-String eingebettet. Sonderzeichen wie `_`, `*`, `[` oder ``` brechen das Parsing.
3. **Dateinamen:** Die Dateinamen für Issues in `issues/active/` könnten noch präziser sein (z.B. inklusive Fehlertyp).

## Lösungsvorschlag
1. **Wiederherstellung:** `get_custom_rate_limit` in `src/db.py` (TELEMETRY_DB) wieder einbauen.
2. **Robustes Markdown:** Import von `telegram.helpers.escape_markdown` und Anwendung auf alle dynamischen Felder in der Admin-Benachrichtigung.
3. **Verbessertes Issuemanagement:** In `src/admin.py` den Dateinamen um den Error-Typ ergänzen (falls extrahierbar).

## Umsetzungsschritte

### 1. `src/db.py`
- Funktion `get_custom_rate_limit(user_id: int)` wieder hinzufügen (Lookup in `users`-Tabelle der `STATE_DB`, da `custom_rate_limit` dort liegt). *Korrektur: `custom_rate_limit` liegt in `users` (STATE_DB).*

### 2. `src/bot.py`
- `from telegram.helpers import escape_markdown` hinzufügen.
- In `_error_handler` die Felder `user_info`, `user_input` und `error_msg` escapen.

### 3. `src/admin.py`
- `save_issue_from_log` anpassen: Dateiname soll Format `error-<Type>-<Message>-<Timestamp>.md` haben.

## Verifizierung & Testing
1. Ausführen von `PYTHONPATH=. uv run python scripts/repro_error_issues.py`.
2. Manueller Test eines Fehlers (z.B. unbekanntes Kommando provozieren), um Admin-Benachrichtigung zu prüfen.
