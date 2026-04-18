# Spec: Modularer Sync-Befehl

## Zielsetzung
Der `/sync` Befehl soll modularisiert werden, damit Admins gezielt nur Teile der Datenbank aktualisieren können (Kurse oder Dozenten). Dies spart Zeit und Ressourcen (API-Calls), wenn nur eine Kategorie veraltet ist.

## Technische Änderungen

### 1. `src/admin.py`
- Modifikation von `cmd_sync(update, context)`:
    - Auswerten von `context.args`.
    - Erlaubte Parameter: `all` (Standard), `courses`, `lecturers`.
    - Anpassung der `_bg_sync` Hilfsfunktion, um basierend auf dem Parameter nur die entsprechenden `raumzeit.build_...` Funktionen aufzurufen.
    - Aktualisierung der Rückmeldenachricht an den Admin, um anzuzeigen, was genau synchronisiert wurde.

### 2. `src/bot.py`
- Aktualisierung der `_ADMIN_COMMANDS` Liste und des Hilfetextes, um die neuen Optionen für `/sync` zu dokumentieren.

## Datenmodell
Keine Änderungen an der Datenbank erforderlich.

## Test-Strategie
1. `/sync courses`: Verifizieren, dass nur der Kurs-Index-Aufbau im Log erscheint.
2. `/sync lecturers`: Verifizieren, dass nur der Dozenten-Index-Aufbau im Log erscheint.
3. `/sync` oder `/sync all`: Verifizieren, dass beide Prozesse nacheinander ablaufen.
4. Fehlerfall: Ungültiger Parameter (z.B. `/sync foo`) -> Hilfemeldung anzeigen.

## Wichtige Mandate
- Die asynchrone Ausführung im Hintergrund (`asyncio.create_task`) muss erhalten bleiben, damit der Bot währenddessen für andere Nutzer erreichbar bleibt.
