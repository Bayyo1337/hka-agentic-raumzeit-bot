# Problem: Unübersichtliche Fakultätsliste bei /setcourse

## Hintergrund & Motivation
Nutzer beschweren sich darüber, dass bei `/setcourse` zu viele irrelevante Einheiten (Dezernate, Institute, Verwaltung) angezeigt werden. Dies erschwert die Auswahl des Studiengangs erheblich.

## Ursachenanalyse / Ist-Zustand
- Die Raumzeit-API liefert unter `/api/v1/departments/public` alle organisatorischen Einheiten der Hochschule (aktuell 57 Stück).
- Die echten Fakultäten sind in den Rohdaten durch das Flag `"faculty": true` gekennzeichnet.
- Der Bot filtert aktuell nicht und zeigt alle 57 Einheiten an.

## Lösungsvorschlag
Implementierung eines Filters in der Bot-Logik, der nur Einheiten berücksichtigt, die das Attribut `faculty: true` besitzen.

## Umsetzungsschritte

### 1. `src/bot.py`
- In der Funktion `_show_faculty_selection`: Die Liste `faculties` filtern, bevor die Inline-Buttons erstellt werden.
- Code-Änderung: `faculties = [f for f in faculties if f.get("faculty")]`.

## Verifizierung & Testing
1. Ausführen des Inspektions-Skripts `scripts/inspect_departments.py`.
2. Manueller Test von `/setcourse`: Die Liste darf nur noch die 6 Fakultäten (AB, EIT, IMM, IWI, MMT, W) enthalten.
