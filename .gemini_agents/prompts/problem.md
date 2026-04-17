# Bugfix: Konflikt-Filter für Basis- und Ziel-Semester

## Hintergrund & Motivation
Nutzer möchten oft prüfen, ob ihr aktueller Stundenplan (z.B. Semester 7) mit einem speziellen Fach aus einem anderen Semester (z.B. Thermodynamik aus Semester 3) kollidiert. Aktuell wird der `module_filter` jedoch nur auf das Basis-Semester angewendet. Wenn das gesuchte Fach dort nicht existiert (da es im Ziel-Semester liegt), bricht die Suche mit einer Fehlermeldung ab.

## Ursachenanalyse / Ist-Zustand
Das Ergebnis des Repro-Skripts bestätigt:
`FAILED: Keine Vorlesungen für das Basis-Semester mit dem Filter 'thermodynamik' gefunden.`

In `src/conflicts.py` wird der Filter hart auf `base_events` angewendet:
```python
    if module_filter:
        f = module_filter.lower()
        base_events = [
            e for e in base_events
            if f in (e.get("name") or "").lower() or f in (e.get("module") or "").lower()
        ]
```
Wenn `base_events` danach leer ist, folgt der Abbruch, selbst wenn das Fach im `target_sem` vorhanden wäre.

## Lösungsvorschlag
Der Filter sollte intelligenter angewendet werden:
1. Prüfe, ob der Filter auf Module im **Basis-Semester** passt. Wenn ja, filtere das Basis-Semester (Standard-Verhalten).
2. Falls nicht, prüfe, ob der Filter auf Module im **Ziel-Semester** passt. Wenn ja, filtere das Ziel-Semester und behalte das Basis-Semester ungefiltert bei.
3. Falls der Filter auf keines von beiden passt, gib die Fehlermeldung aus.

Zusätzlich sollte die radikale Normalisierung aus `gemini.md` verwendet werden, um Tippfehler oder Sonderzeichen robuster zu handhaben.

## Umsetzungsschritte
1. **Normalisierungs-Funktion hinzufügen** (falls nicht vorhanden oder aus `tools.py` importieren).
2. **Filter-Logik in `src/conflicts.py` anpassen**:
   - `base_matches` extrahieren.
   - Falls leer, `target_matches` extrahieren.
   - Entsprechend `base_events` oder `target_events` einschränken.
3. **Fehlermeldung verfeinern**, falls gar nichts gefunden wurde.

## Verifizierung & Testing
- Ausführen des Repro-Skripts `scripts/repro_issue.py` (erwarteter Erfolg nach Fix).
- Testen mit einem Filter, der im Basis-Semester liegt.
- Testen mit einem Filter, der in gar keinem Semester liegt (erwarteter Fehler).
