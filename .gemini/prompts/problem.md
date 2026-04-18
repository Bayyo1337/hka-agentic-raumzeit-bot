# Issue: Raumnummern werden nicht ausgegeben und fehlerhaft gescraped

## Hintergrund & Motivation
Nutzer haben gemeldet, dass Raumnummern (Büros) von Dozenten nicht angezeigt werden. Zudem zeigt eine Analyse des Dozenten-Index (`data/lecturers.json`), dass der Scraper oft Sprechzeiten oder andere Texte fälschlicherweise als "Raum" erfasst.

## Ursachenanalyse / Ist-Zustand
Die Untersuchung hat zwei Hauptursachen ergeben:

1. **Fehlende Weitergabe in der API-Logik**: Die Funktionen `get_lecturer_timetable` und `get_lecturer_info` laden zwar die Dozenten-Infos aus dem Index, geben das Feld `room` aber nicht an den Aufrufer (und damit an den Formatter) weiter.
   * *Ergebnis Repro-Skript*: `Raum im Ergebnis: MISSING` obwohl im Index vorhanden.

2. **Ungenauer Scraper-Regex**: Der Regex in `build_lecturer_index` zur Extraktion von Räumen von den HKA-Profilseiten ist zu unscharf. Er fängt oft Texte ein, die zwar das Wort "Raum" enthalten, aber keine Raumnummern sind (z.B. "In Coronazeiten bitte Termin vorab...").
   * *Beispiel*: `"room": "Mo bis Do, 09:00 bis 13:00 Uhr..."`

## Lösungsvorschlag

1. **API-Logik anpassen**: In `src/tools.py` das Feld `room` in den Rückgabe-Dictionaries von `get_lecturer_timetable` und `get_lecturer_info` ergänzen.
2. **Scraper verbessern**:
   * Den Regex für Räume in `src/tools.py` verfeinern (z.B. durch Längenbegrenzung oder Ausschluss von typischen Sprechzeit-Keywords).
   * Die radikale Normalisierung aus `gemini.md` ist hier primär für den Vergleich wichtig, für die Anzeige von Räumen sollte der Originaltext (geputzt) erhalten bleiben.
3. **Formatter prüfen**: Sicherstellen, dass der Formatter das `room`-Feld bei Dozenten-Infos auch wirklich rendert (scheint laut Grep bereits der Fall zu sein).

## Umsetzungsschritte

1. **src/tools.py**:
   * In `get_lecturer_timetable` das Feld `"room": info.get("room")` hinzufügen.
   * In `get_lecturer_info` das Feld `"room": info.get("room")` hinzufügen.
   * Den `room_pattern` Regex in `_fetch_sprechzeit` (innerhalb von `build_lecturer_index`) verbessern.
2. **src/formatter.py**: Kurze Sichtprüfung, ob `room` in `_fmt_lecturer_info` oder ähnlichem genutzt wird.

## Verifizierung & Testing
- Ausführen von `scripts/repro_room_scraping.py`.
- Nach der Änderung sollte der Raum (sofern im Index vorhanden) korrekt ausgegeben werden.
- (Optional) Manueller Sync-Lauf für einzelne Dozenten, um den verbesserten Scraper zu testen.
