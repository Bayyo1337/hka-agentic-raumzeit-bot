# Problem: Mensa-Allergen-Abfrage schlägt fehl (Race Condition & Kalt-Start)

## Hintergrund & Motivation
Nutzer möchten nach Allergenen fragen können, ohne vorher explizit den Speiseplan (`/mensa`) abzurufen. Aktuell liefert `get_mensa_meal_details` einen Fehler, wenn die Datenbank für den heutigen Tag noch nicht befüllt wurde. Zudem treten Race Conditions auf, wenn das LLM beide Tools (`get_mensa_menu` und `get_mensa_meal_details`) gleichzeitig aufruft.

## Ursachenanalyse / Ist-Zustand
1. **Kalt-Start:** Wenn der Bot neu gestartet wurde oder der Tag gewechselt hat, ist der Cache in `mensa_meals` leer. `get_mensa_meal_details` prüft nur den Cache und gibt bei Misserfolg eine Fehlermeldung zurück.
2. **Race Condition:** Da Tools via `asyncio.gather` parallel ausgeführt werden, greift `get_mensa_meal_details` oft auf die DB zu, bevor `get_mensa_menu` seine Ergebnisse persistiert hat.
3. **Ergebnis Repro-Skript:** Bestätigt, dass ein direkter Aufruf von `get_mensa_meal_details` bei leerer DB fehlschlägt.

## Lösungsvorschlag
1. **Auto-Warming:** Wenn `get_mensa_meal_details` keine Daten für heute in der DB findet, soll es intern einmalig `get_mensa_menu()` aufrufen, um den Cache zu befüllen.
2. **Synchronisierung:** Einführung eines `asyncio.Lock`, um sicherzustellen, dass nur eine Instanz gleichzeitig den Cache befüllt (Vermeidung von redundanten API-Calls).
3. **Retry-Logik:** Kurzes Warten und erneuter Check, falls eine parallele Schreiboperation erkannt wird.

## Umsetzungsschritte

### 1. `src/tools.py`
- Globalen `_MENSA_LOCK = asyncio.Lock()` hinzufügen.
- `get_mensa_meal_details` anpassen:
    - Innerhalb des Locks prüfen, ob `today_meals` in der DB existieren.
    - Falls nein: `await get_mensa_menu()` aufrufen.
    - Falls ja: Normal fortfahren.
- `get_mensa_menu` ebenfalls mit dem Lock absichern, um doppelte API-Abfragen bei parallelen Aufrufen zu vermeiden.

## Verifizierung & Testing
1. Ausführen des Repro-Skripts `scripts/repro_mensa_no_menu.py`. Es muss nach der Änderung Erfolg melden.
2. Manueller Test im Bot: "Welche Allergene hat Wahlessen 2?" als allererste Nachricht des Tages.
