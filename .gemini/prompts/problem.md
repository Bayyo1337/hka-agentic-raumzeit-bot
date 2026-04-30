# Problem: Fehlerhafte Extraktion von Dozenten-Kürzeln

## Hintergrund & Motivation
Wenn das LLM IDs halluziniert (z. B. `offer0001` für Offermann), schneidet der Bot aktuell den ersten Buchstaben ab (`ffer0001`), weil die Regex `[a-z]{4}\d{4}` unpräzise ist. Dies führt zu Verwirrung und verhindert einen sauberen Fallback auf die Namenssuche.

## Ursachenanalyse / Ist-Zustand
- **Regex-Fehler:** `re.search(r'([a-z]{4}\d{4})', q_lower)` findet in `offer0001` den Teilstring `ffer0001`, da er genau 4 Buchstaben gefolgt von 4 Ziffern enthält.
- **Folge:** Da `ffer0001` nicht im Index ist, schlägt der gesamte Prozess fehl, anstatt auf die Suche nach dem Namen "Offermann" zurückzufallen.

## Lösungsvorschlag
1. **Regex-Härtung:** Die Regex muss sicherstellen, dass vor den 4 Buchstaben kein weiterer Buchstabe steht. Nutzung von `(?<![a-z])` (Lookbehind) oder Wortgrenzen.
2. **Präzisierung:** Umstellung auf `re.search(r'\b([a-z]{4}\d{4})\b', q_lower)`, um sicherzustellen, dass nur exakte Kürzel gematcht werden.
3. **LLM-Guidance:** Anpassung der `TOOL_DEFINITIONS`, um dem LLM explizit zu verbieten, Kürzel zu raten.

## Umsetzungsschritte

### 1. `src/tools.py`
- In `_resolve_account` (um Zeile 300):
  - Ändere `re.search(r'([a-z]{4}\d{4})', q_lower)` zu `re.search(r'\b([a-z]{4}\d{4})\b', q_lower)`.
- In `TOOL_DEFINITIONS`:
  - `get_lecturer_timetable`: "WICHTIG: Nutze den Namen des Dozenten. Rate NIEMALS Kürzel!"

## Verifizierung & Testing
1. Ausführen des korrigierten `scripts/repro_lecturer_id.py`. Es darf kein Match für `offer0001` mehr finden.
2. Test mit echtem Namen "Offermann" muss weiterhin funktionieren.
