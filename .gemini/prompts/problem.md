# Problem: Mensa-Allergen-Abfrage schlägt bei Kaltstart fehl

## Hintergrund & Motivation
Nutzer erhalten einen Fehler ("Bitte frage erst nach dem Menü"), wenn sie als allererstes nach Allergenen fragen. Mein erster Fix hat zwar `get_mensa_menu` aufgerufen, aber danach wurde die Suche nicht korrekt wiederholt. Zudem wurden API-Fehler verschluckt.

## Ursachenanalyse / Ist-Zustand
In `get_mensa_meal_details`:
1. Wenn die DB leer ist, wird `get_mensa_menu()` aufgerufen.
2. Danach wird zwar `today_meals` neu geladen, aber die UUID-Prüfung (Schritt 2/3) wird nicht wiederholt.
3. Falls `get_mensa_menu()` einen Fehler zurückgibt (z.B. API-Timeout), wird dieser ignoriert und am Ende die generische Fehlermeldung "Bitte frage erst nach dem Menü" ausgegeben.

## Lösungsvorschlag
1. **Zweistufiger Prozess:** 
   - Stufe 1: Falls DB leer ist -> `get_mensa_menu()` rufen.
   - Falls dieses fehlschlägt -> API-Fehler zurückgeben.
   - Stufe 2: Falls erfolgreich -> `get_mensa_meal_details` rekursiv aufrufen (mit einem Flag `is_retry=True`), um den gesamten Suchvorgang inklusive RAM- und DB-Checks sauber zu wiederholen.
2. **Synchronisierung:** Beibehaltung des `_MENSA_LOCK`, um Mehrfach-Aufrufe der API zu vermeiden.

## Umsetzungsschritte

### 1. `src/tools.py`
- Überarbeitung von `get_mensa_meal_details(meal_id, is_retry=False)`:
  - Zuerst RAM-Check.
  - Dann DB-UUID-Check.
  - Falls nichts gefunden und `not is_retry`:
    - Lock erwerben.
    - Prüfen ob DB immer noch leer.
    - Falls ja: `await get_mensa_menu()` ausführen.
    - Falls API-Fehler -> diesen zurückgeben.
    - Falls Erfolg -> `return await get_mensa_meal_details(meal_id, is_retry=True)`.
  - Erst danach Fallback-Logiken (Line-Match, Fuzzy-Name).

## Verifizierung & Testing
1. Ausführen von `scripts/repro_mensa_coldstart.py`. Es sollte nun (bei API-Fehlern) den API-Fehler zeigen oder (bei Erfolg) das Gericht finden.
2. Manueller Test: Erstabfrage eines Gerichts.
