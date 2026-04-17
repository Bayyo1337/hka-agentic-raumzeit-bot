# Sync-Performance Fix für h-ka.de Dozenten-Index

## Hintergrund & Motivation
Die Synchronisierung des Dozenten-Index von `h-ka.de` ist extrem langsam (ca. 10 Minuten pro Seite) oder hängt komplett. Dies liegt an einem ineffizienten Regulären Ausdruck (`tr_pattern`) in `src/tools.py`, der auf eine 300KB große HTML-Seite angewendet wird. Durch "Catastrophic Backtracking" bei fehlerhaften oder fehlenden Matches wird die CPU-Last maximiert und der Prozess blockiert.

## Ursachenanalyse / Ist-Zustand
Der aktuelle Regex in `src/tools.py`:
```python
tr_pattern = r'<tr[^>]*data-document-url="(.*?)"[^>]*>.*?<span class="person__user-academic-title">(.*?)</span>.*?<span class="person__user-name-title">(.*?)</span>.*?([\w.\-]+)<span[^>]*>spam prevention</span>@h-ka\.de'
```

Probleme:
1. **Fehlende Felder:** Das Feld `<span class="person__user-name-title">` scheint in der aktuellen HTML-Struktur von `h-ka.de` nicht mehr (oder nicht in jeder Zeile) vorhanden zu sein.
2. **Backtracking:** Die Kombination aus mehreren `.*?` und `re.DOTALL` auf einem riesigen String führt dazu, dass der Regex-Engine bei einem Nicht-Match (z.B. wenn ein Span fehlt) versucht, alle möglichen Kombinationen bis zum Ende des Dokuments zu prüfen.
3. **Struktur:** Die Seite enthält ca. 20 Personen pro Seite, aber der Regex wird auf den gesamten Content angewendet.

## Lösungsvorschlag
Statt eines riesigen Regex auf dem gesamten Dokument wird ein zweistufiges Verfahren verwendet:
1. **Splitting:** Das Dokument wird in einzelne `<tr>` Blöcke zerlegt. Da die Blöcke sauber mit `</tr>` enden, ist dies sicher und schnell.
2. **Extraktion:** Auf jedem Block werden gezielte, einfache Regex-Suchen für die einzelnen Felder (URL, Titel/Name, Email) ausgeführt.
3. **Robustheit:** Wenn ein Feld (z.B. Titel) fehlt, wird dies abgefangen, ohne den gesamten Prozess zu stoppen.

## Umsetzungsschritte
1. **`src/tools.py` anpassen:**
    - Ersetzen der `re.findall(tr_pattern, ...)` Schleife durch eine Logik, die erst die Zeilen isoliert.
    - Verwendung von spezifischen Patterns für `data-document-url`, `person__user-academic-title` und die Email.
2. **Normalisierung:** Sicherstellen, dass die Namen weiterhin normalisiert werden (bestehende Logik beibehalten).
3. **Validierung:** Ausführen des Repro-Skripts `scripts/repro_sync_hka.py` (angepasst an die neue Logik) zur Zeitmessung.

## Verifizierung & Testing
- `python3 scripts/repro_sync_hka.py` muss in unter 1 Sekunde für Seite 1 fertig sein.
- `uv run python -m py_compile src/tools.py` zur Syntax-Prüfung.
- Manueller Test des Sync-Befehls (falls möglich) oder Verifizierung der Log-Ausgaben.
