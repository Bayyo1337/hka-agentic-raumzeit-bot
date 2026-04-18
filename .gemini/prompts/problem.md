# Sync Performance Optimierung

## Hintergrund & Motivation
Der Synchronisierungsvorgang des Dozenten-Index ist aktuell extrem zeitaufwendig (ca. 7-10 Minuten für ~1300 Personen). Da dieser Index wöchentlich oder manuell aktualisiert wird, behindert die lange Dauer die Wartbarkeit und Nutzererfahrung (falls Admins auf den Abschluss warten).

## Ursachenanalyse / Ist-Zustand
Das Ergebnis des Performance-Tests (`scripts/perf_sync_optim.py`) und die Code-Analyse zeigen folgende Probleme:
1. **Ineffiziente HTTP-Clients**: In `_fetch_sprechzeit` wird für jeden einzelnen Dozenten ein neuer `httpx.AsyncClient` erstellt. Dies verhindert Connection Pooling und erzwingt für jeden Request einen neuen SSL-Handshake.
2. **Starres Batching**: Die aktuelle Logik verarbeitet 20 Dozenten gleichzeitig und pausiert dann hart für 0.5 Sekunden. Dies führt zu unnötigen Leerlaufzeiten zwischen den Batches.
3. **Konkurrierende Requests**: Das Batching ist zwar sicher, aber nicht optimal für den Durchsatz.

## Lösungsvorschlag
1. **Shared HTTP Client**: Erstellung eines einzigen `httpx.AsyncClient` innerhalb von `build_lecturer_index`, der an die Worker-Funktion übergeben wird.
2. **Semaphor-basierte Parallelisierung**: Ersetzen des Batch-Loops durch eine Semaphor-Steuerung (`asyncio.Semaphore(20)`). Dies erlaubt es, konstant 20 Requests "in der Leitung" zu haben. Sobald einer fertig ist, startet der nächste, ohne auf den Rest des Batches zu warten.
3. **Logging-Optimierung**: Beibehaltung der Fortschrittsanzeige, aber basierend auf einem Zähler statt der Batch-Index-Logik.

## Umsetzungsschritte
1. **src/tools.py**:
    - `_fetch_sprechzeit` anpassen, um den `client` als Argument zu akzeptieren.
    - `build_lecturer_index` umbauen:
        - `httpx.AsyncClient` als `async with` Block um die gesamte Scraping-Logik legen.
        - `asyncio.Semaphore` verwenden, um die Gleichzeitigkeit zu begrenzen.
        - Fortschritts-Logging anpassen.

## Verifizierung & Testing
- Ausführen von `scripts/perf_sync_optim.py` zur Bestätigung des Prinzips (bereits erfolgt).
- Manueller Test-Sync (Dozenten): `uv run python -c "import asyncio, src.tools as t; asyncio.run(t.build_lecturer_index())"`
- Zeitmessung vor/nach der Optimierung.
