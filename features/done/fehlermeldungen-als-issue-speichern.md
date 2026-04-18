# Spec: Fehlermeldungen direkt als Active Issue speichern

## Zielsetzung
Wenn im Bot ein technischer Fehler auftritt, sollen Admins die Möglichkeit haben, diesen Fehler sowie den dazugehörigen Kontext (Log, Traceback, Usereingabe) per Knopfdruck als Active Issue in `issues/active/` zu speichern. Dies beschleunigt das Bugtracking erheblich.

## Technische Änderungen

### 1. `src/bot.py`
- **Error Cache**: Einführung eines globalen In-Memory Caches `_error_cache: dict[str, dict]`, um Fehlerdetails kurzzeitig zu speichern (Key ist eine UUID).
- **`_error_handler`**: 
    - Wenn der Nutzer ein Admin ist (oder bei jedem Fehler, falls wir Admins global benachrichtigen wollen):
    - Erzeuge eine UUID für den Fehler.
    - Speichere Exception, Traceback, Usereingabe (falls vorhanden) und Zeitstempel im Cache.
    - Sende dem Admin eine Nachricht mit der Fehlermeldung und einem Inline-Button "Issue erstellen".
- **`handle_callback`**:
    - Reagiere auf den Callback `err_save:<uuid>`.
    - Rufe `admin.save_issue_from_log(uuid, cache_entry)` auf.
    - Informiere den Admin über Erfolg oder Misserfolg.

### 2. `src/admin.py`
- **`save_issue_from_log(uuid, data)`**:
    - Generiere einen kurzen, prägnanten Dateinamen aus der Fehlermeldung (z.B. `error-attributeerror-none-type.md`).
    - Formatiere die Daten als Markdown:
        - Titel (Fehlertyp)
        - Zeitstempel
        - Usereingabe
        - Vollständiger Traceback
    - Speichere die Datei unter `issues/active/<filename>`.
    - Nutze radikale Normalisierung für den Dateinamen (nur a-z0-9 und Bindestriche).

## Datenmodell
Keine Datenbankänderungen erforderlich, da die Issues im Dateisystem gespeichert werden.

## Test-Strategie
1. Provozieren eines Fehlers im Bot (z.B. durch ein ungültiges Tool-Argument oder künstlichen Fehler im Agent).
2. Verifizieren, dass der Admin eine Nachricht mit Button erhält.
3. Klicken des Buttons und Verifizieren, dass eine neue Datei in `issues/active/` erscheint, die alle relevanten Informationen enthält.

## Sicherheit
- Der Button zum Speichern darf **nur** Admins angezeigt werden.
- Der Callback-Handler muss erneut prüfen, ob der ausführende Nutzer Admin-Rechte hat.
