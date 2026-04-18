# Issue: Raumnummern auf HKA-Profilseiten werden nicht korrekt gescraped

## Hintergrund & Motivation
Nutzer berichten, dass Raumnummern (z.B. Peter Offermann, M-012) nicht im Bot angezeigt werden. Eine Analyse der HKA-Profilseiten hat ergeben, dass die HTML-Struktur von der aktuellen Scraping-Logik nicht abgedeckt wird.

## Ursachenanalyse / Ist-Zustand
Der aktuelle Regex in `src/tools.py`:
```python
room_pattern = r'(?:Raum|Büro)\s*:\s*(?:<br\s*/?>\s*)?(.*?)\s*(?:</p>|<strong>|<li>)'
```
Probleme:
1. **Fehlender Doppelpunkt**: Die Webseite nutzt oft `Raum` (ohne Doppelpunkt) gefolgt von einem Zeilenumbruch.
2. **Zeilenumbrüche/Whitespace**: Zwischen dem Wort "Raum" und der eigentlichen Nummer (z.B. "M-012") liegen oft mehrere Leerzeichen und Newlines.
3. **Abschluss-Tag**: Die Raumnummer wird oft durch ein `<br/>` abgeschlossen, was im aktuellen Regex nur als optionaler *Start* vorgesehen war.

*Ergebnis Repro-Skript*:
```html
<p>
    Raum
    M-012<br/>
</p>
```
Der aktuelle Regex findet hier keinen Match, da er einen Doppelpunkt erwartet und die Newlines nicht flexibel genug handhabt.

## Lösungsvorschlag
Verwendung eines robusten Regex, der:
1. Den Doppelpunkt optional macht.
2. Beliebige Whitespaces (inkl. Newlines) nach "Raum" erlaubt.
3. Den Inhalt bis zum nächsten `<br/>` oder Schließ-Tag (`</p>`, `</div>`) erfasst.

Neuer Regex-Entwurf:
```python
r'(?:Raum|Büro)\s*:?\s*(?:<br\s*/?>\s*)?([A-Z0-9.\- ]+)\s*(?:<br\s*/?>|</p>|</div>|<strong>|<li>)'
```
Zusätzlich sollte der Plausibilitätscheck (Länge < 30) beibehalten werden.

## Umsetzungsschritte
1. **src/tools.py**:
   - Den `room_pattern` Regex in `_fetch_sprechzeit` (innerhalb von `build_lecturer_index`) aktualisieren.
   - Den `person__user-name-title` Regex in `build_lecturer_index` prüfen, da dieser im Test `MISSING` lieferte.

## Verifizierung & Testing
1. Ausführen des Repro-Skripts `scripts/repro_room_structure.py` mit dem neuen Regex.
2. Manueller Test-Lauf eines Teil-Syncs für betroffene Dozenten.
