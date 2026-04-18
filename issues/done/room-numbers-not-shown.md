# Issue: Room numbers not shown (Scraping logic failed)

## Problem
Raumnummern wurden für viele Dozenten (z.B. Peter Offermann) nicht gescraped, da der Regex an Zeilenumbrüchen und fehlenden Doppelpunkten auf den HKA-Profilseiten scheiterte. Zudem wurden Namen im Index als `MISSING` markiert, da sich die CSS-Klassen auf der HKA-Webseite geändert hatten.

## Lösung
1. **Robusterer Raum-Regex**: Der Regex in `src/tools.py` wurde von einer gierigen `.*?` Logik auf eine stoppende Logik umgestellt (`[^<]+`), die beim nächsten HTML-Tag abbricht. Zudem wurde der Doppelpunkt optional gemacht, um verschiedene Varianten der Webseite zu unterstützen.
2. **Fix Namens-Extraktion**: Der Scraper nutzt nun `person__user-academic-title` anstelle der veralteten Klasse `person__user-name-title`, um Namen und Titel korrekt aus der Personenliste zu extrahieren.
3. **Plausibilitäts-Check**: Der bestehende Check (Länge < 30 Zeichen, keine Uhrzeiten) sorgt weiterhin dafür, dass keine Sprechzeiten fälschlicherweise als Raum übernommen werden.

## Verifizierung
- Erfolgreich mit `scripts/repro_room_structure.py` und `scripts/test_offermann_fix.py` an Realdaten von der HKA-Webseite getestet.
- Peter Offermann (M-012) und Marcus Aberle (B-310A) werden nun korrekt erkannt.
