# Issue: Room numbers are not scraped (and not displayed)

## Problem
Raumnummern (Büros) von Dozenten wurden in den API-Antworten und im Telegram-Bot nicht angezeigt. Zudem war der Scraper für h-ka.de Profilseiten zu ungenau und hat oft Sprechzeiten als Raumnummer erfasst.

## Lösung
1. **API-Erweiterung**: In `src/tools.py` wurden `get_lecturer_timetable` und `get_lecturer_info` so angepasst, dass sie das `room`-Feld aus dem Dozenten-Index zurückgeben.
2. **Scraper-Verfeinerung**: Der Regex in `build_lecturer_index` wurde durch einen Plausibilitätscheck ergänzt (Längenbegrenzung auf 30 Zeichen, Ausschluss von Keywords wie "Uhr" oder "Termin"), um Rauschen zu reduzieren.
3. **UI-Anpassung**: `src/formatter.py` wurde aktualisiert, um das Büro im Stundenplan und in der Dozenten-Info anzuzeigen.

## Verifizierung
- Erfolgreich verifiziert mit `scripts/repro_room_scraping.py`.
- Syntax- und Linting-Checks bestanden.
