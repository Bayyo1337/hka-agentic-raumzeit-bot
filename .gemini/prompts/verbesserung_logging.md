# Verbesserung der Log-Transparenz (Shutdown & Sync)

## Hintergrund & Motivation
Nutzer und Admins haben Schwierigkeiten zu verstehen, was während langlaufender Prozesse passiert.
1. **Shutdown**: Der Bot braucht ca. 5-10 Sekunden zum Beenden, ohne Feedback zu geben, welcher Teil (Polling, Tasks, DB) die Verzögerung verursacht.
2. **Kurs-Index Sync**: Die Fortschrittsanzeige in Phase 1 und 2 ist rein numerisch ("200/640"). Es fehlt der Kontext, welcher Studiengang oder welches Semester gerade verarbeitet wird.

## Ursachenanalyse / Ist-Zustand
- **Shutdown**: In `src/bot.py` werden `app.updater.stop()`, `app.stop()` und `app.shutdown()` in einer Zeile ohne Logging aufgerufen.
- **Sync**: In `src/tools.py` (`build_course_index`) wird in den Batch-Loops nur der Zähler `i` geloggt, aber nicht die Daten aus dem aktuellen Batch.

## Lösungsvorschlag
### 1. Shutdown (src/bot.py)
- Aufspalten der Shutdown-Befehle in `main_async`.
- Hinzufügen von `log.debug`-Ausgaben vor jedem Schritt.

### 2. Kurs-Index Sync (src/tools.py)
- **Phase 1**: In der Log-Meldung das Kürzel des ersten Studiengangs im aktuellen Batch anzeigen.
- **Phase 2**: In der Log-Meldung das Basis-Semester (`abbr.sem`) des aktuellen Batches anzeigen.

## Umsetzungsschritte
1. **src/bot.py**:
   - `await app.updater.stop(); await app.stop(); await app.shutdown()` ersetzen durch detaillierte Aufrufe mit Logging.
2. **src/tools.py**:
   - Anpassung der `log.info`-Aufrufe in `build_course_index`.

## Verifizierung & Testing
- **Shutdown**: Bot starten, `exit` eingeben und Zeitstempel der Debug-Logs prüfen.
- **Sync**: `uv run python -c "import asyncio, src.tools as t; asyncio.run(t.build_course_index())"` ausführen und die neuen Log-Meldungen validieren.
