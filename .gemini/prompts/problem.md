# Problem: Maschinenbau wird nicht zu MABB aufgelöst

## Status Quo
In `src/tools.py` gibt es die Funktion `resolve_course_name`, die einen nutzergegebenen String (z.B. "Maschinenbau") in ein offizielles HKA-Kürzel (z.B. "MABB") umwandeln soll.

Aktuell prüft die Funktion nur das Feld `name` (Kürzel) auf exakte Übereinstimmung nach Normalisierung. Das Feld `longName` wird ignoriert.

## Symptom
Wenn ein Nutzer `find_timetable_conflicts` mit "Maschinenbau" aufruft, schlägt die Auflösung fehl:
`❌ Studiengang Maschinenbau konnte nicht zugeordnet werden`

## Ursache
Die Implementierung von `resolve_course_name` in `src/tools.py` ist unvollständig:
```python
    # Teil-Match auf Name
    for c in courses:
        # Manche Kurse haben 'shortName' oder 'description'?
        # In der HKA API ist 'name' oft das Kürzel (z.B. MABB)
        # Wir bräuchten eigentlich eine Liste der Klarnamen.
        pass
```
Der `longName` wird zwar von `get_courses_of_study` zurückgegeben, aber nicht für das Matching verwendet.

## Ziel
`resolve_course_name` soll:
1.  Zuerst exakt auf `name` (Kürzel) prüfen.
2.  Danach prüfen, ob der Query-String im `longName` enthalten ist (Teil-Match).
3.  Bei mehreren Treffern (z.B. "Maschinenbau (B)" vs "Maschinenbau (M)") eine sinnvolle Heuristik anwenden oder den ersten Treffer nehmen (meist Bachelor).

## Plan
1.  Anpassen von `resolve_course_name` in `src/tools.py`:
    *   Schleife über `courses` erweitern.
    *   Normalisierten `query` gegen normalisierten `longName` prüfen.
    *   Falls ein Match gefunden wird, das zugehörige `name` (Kürzel) zurückgeben.
2.  Validierung mit `repro_issue.py`.
