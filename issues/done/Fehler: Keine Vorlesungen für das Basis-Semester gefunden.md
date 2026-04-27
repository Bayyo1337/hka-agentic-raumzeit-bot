# Analyse & Lösung: Keine Vorlesungen für das Basis-Semester gefunden.

## Problem-Analyse
Der Fehler trat in der Funktion `find_timetable_conflicts` auf, wenn für den gewählten Zeitraum (aktuelle Woche) keine Vorlesungen für das Basis-Semester gefunden wurden.

Folgende Ursachen wurden identifiziert:
1. **Extreme Ineffizienz:** Die Funktion rief für jeden der 5 Wochentage separat `fetch_course_brute_force` auf. Jede dieser Abfragen führte einen kompletten Brute-Force-Scan über 38 mögliche Gruppen-Suffixe durch.
   - Pro Konflikt-Check entstanden so bis zu **390 HTTP-Anfragen** (5 Tage * 2 Semester * ~39 Probes).
   - Dies führte zu extremen Ladezeiten und potenziellen Timeouts oder Rate-Limits durch den Server.
2. **Race Condition bei der Authentifizierung:** `_get_token()` hatte kein Lock. Bei hunderten parallelen Anfragen wurden dutzende neue JWT-Token gleichzeitig angefordert, was den Server zusätzlich belastete.
3. **Irreführende Fehlermeldung:** Wenn ein `module_filter` gesetzt war und dieser alle Ergebnisse wegfilterte, war die Fehlermeldung "Keine Vorlesungen für das Basis-Semester gefunden" nicht präzise genug.

## Durchgeführte Fixes

### 1. Authentifizierungs-Lock (`src/tools.py`)
- Ein `asyncio.Lock()` wurde zu `_get_token` hinzugefügt.
- Verhindert, dass parallele Anfragen gleichzeitig den Authentifizierungs-Endpunkt stürmen.

### 2. Optimierung der Konflikt-Suche (`src/conflicts.py`)
- Statt 5 Einzelabfragen pro Tag wird nun **eine einzige Abfrage für die gesamte Woche** pro Semester durchgeführt.
- Die Filterung nach Wochentagen erfolgt lokal im Speicher.
- Reduziert die Anzahl der Anfragen drastisch (von ~390 auf ~76 bei leerem Index, auf **nur 2-6 Anfragen** bei gefülltem Index).

### 3. Intelligentes Brute-Force (`src/tools.py`)
- `fetch_course_brute_force` prüft nun zuerst den Datenbank-Index.
- Nur wenn kein Index für den Kurs vorhanden ist, wird der teure Brute-Force-Scan durchgeführt.
- Timeouts für API-Abfragen wurden von 5s auf bis zu 30s erhöht, um bei langsamer API-Antwort stabil zu bleiben.

### 4. Verbesserte Fehlermeldung (`src/conflicts.py`)
- Die Fehlermeldung unterscheidet nun zwischen "Generell keine Vorlesungen" und "Keine Vorlesungen mit dem angegebenen Filter".

## Validierung
- Erfolgreich getestet mit `INFB 1 vs 2` und `MABB 1 vs 2`.
- Verifiziert, dass der Datenbank-Index korrekt genutzt wird und die Abfragen nun in Sekundenbruchteilen statt nach 10-20 Sekunden abgeschlossen sind.
- Filter-Fehlermeldung verifiziert.

Status: ✅ Gelöst und Optimiert.
