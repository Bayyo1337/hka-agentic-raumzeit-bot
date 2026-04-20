# Spezifikation: Architektur-Refactoring der SQLite-Datenbank (Aufsplittung)

## 1. Ausgangslage & Motivation
Aktuell speichert der HKA Raumzeit KI-Agent alle persistenten Daten – von kritischen Nutzerprofilen über volatile Caches bis hin zu hochfrequenten Telemetrie-Logs – in einer einzigen SQLite-Datenbank (`bot.db`). 

Mit dem stetigen Wachstum des Projekts (zuletzt durch die Integration des persistenten Mensa-Caches) ergeben sich daraus strukturelle und operative Herausforderungen:
- **Locking-Konflikte:** SQLite sperrt auf Datei-Ebene. Jeder Schreibzugriff (z. B. ein neuer Rate-Limit-Eintrag pro User-Nachricht) blockiert potenziell Lesezugriffe auf kritische Caches (wie den Kurs-Index).
- **Fehlende Backup-Granularität:** Ein Backup der `bot.db` umfasst unnötigerweise Gigabytes an Cache-Daten, obwohl eigentlich nur die Nutzerprofile (`users`), Token-Stände (`tokens`) und Gesprächsverläufe (`histories`) gesichert werden müssen.
- **Erschwerte Wartung:** Bei Änderungen am Schema von flüchtigen Caches (z.B. Mensa oder Raumzeit-API) besteht bei Migrations-Scripts immer ein Restrisiko, die kritischen Nutzerdaten zu beschädigen.

## 2. Zielarchitektur: Das 3-Säulen-Modell
Die Datenbank wird anhand der Daten-Lebensdauer, der Wichtigkeit und des I/O-Profils in drei separate SQLite-Dateien unterteilt. Alle Dateien liegen standardmäßig im `data/`-Verzeichnis (bzw. konfigurierbar via `.env`).

### 2.1 Säule 1: `state.db` (Kritische Nutzdaten)
**Charakteristik:** Geringe bis mittlere Schreiblast, hohe Relevanz, oberste Backup-Priorität.
Diese Datenbank enthält den permanenten Zustand des Bots. Ein Verlust dieser Datei würde bedeuten, dass Nutzer ihre Einstellungen verlieren und Gesprächskontexte abreißen.

**Tabellen:**
- `users`: Nutzerprofile, Bann-Status, ausgewählte Studiengänge (`primary_course`).
- `histories`: Der JSON-Gesprächsverlauf für das LLM-Gedächtnis.
- `tokens`: Kumulierter API-Token-Verbrauch (Input/Output) pro Nutzer für das Billing-Monitoring.

### 2.2 Säule 2: `cache.db` (Volatile API-Kopien)
**Charakteristik:** Hohe Leselast, periodische Schreiblast (Syncs), reproduzierbar.
Diese Datenbank fungiert als High-Speed-Proxy vor den externen APIs (Raumzeit, Mensa). Die Daten können bei Verlust jederzeit (wenn auch zeitaufwendig) neu generiert werden.

**Tabellen:**
- `course_index`: Alle validen Studiengangs-Kombinationen (Kürzel, Semester, Gruppe).
- `mensa_meals`: Persistierter Speiseplan inkl. Allergenen (ermöglicht kontextfreie Detailabfragen).
- `user_plan_cache`: Zwischengespeicherte, fertig gerenderte Tages-Stundenpläne (TTL: ~4 Stunden).

### 2.3 Säule 3: `telemetry.db` (Metriken & Logs)
**Charakteristik:** Extrem hohe Schreiblast, sehr kurze Lebensdauer, automatische Bereinigung.
Hier landen alle Daten, die für den laufenden Betrieb und das Rate-Limiting relevant sind, aber nach kurzer Zeit ihren Wert verlieren.

**Tabellen:**
- `requests`: Zeitstempel jedes eingehenden Commands zur Durchsetzung des Spam-Schutzes (Rate-Limit).
- `test_cases`: Gesammelte Test-Queries für Regressionstests (optional).

## 3. Technische Umsetzung in `src/db.py`

### 3.1 Pfad-Verwaltung
Die bisherige Konstante `DB_PATH` wird abgelöst. Stattdessen nutzt das Modul ein Basis-Verzeichnis:
```python
DB_DIR = os.environ.get("DB_DIR", "data")
STATE_DB = os.path.join(DB_DIR, "state.db")
CACHE_DB = os.path.join(DB_DIR, "cache.db")
TELEMETRY_DB = os.path.join(DB_DIR, "telemetry.db")
```

### 3.2 Initialisierung & Migration (`init()`)
Die `init()`-Funktion wird in drei logische Blöcke unterteilt, die jeweils ihre eigene SQLite-Verbindung öffnen und das spezifische Schema anlegen.
Um Abwärtskompatibilität zu gewährleisten, wird beim ersten Start ein **Migrations-Skript** ausgeführt:
1. Prüfen, ob eine alte `logs/bot.db` oder `data/bot.db` existiert.
2. Falls ja:
   - Die alte Datei wird nach `data/state.db` kopiert/umbenannt.
   - Aus der neuen `state.db` werden alle Tabellen ge-`DROP`ped, die nach `cache.db` oder `telemetry.db` gehören.
   - Die Initialisierung legt dann `cache.db` und `telemetry.db` neu und leer an. (Ein Neuaufbau des Caches ist akzeptabel).

### 3.3 Connection-Management
Die bestehenden Funktionen in `src/db.py` (z.B. `get_user`, `save_mensa_meals`, `check_rate_limit`) werden so angepasst, dass sie sich explizit mit der jeweils richtigen Datenbank-Datei verbinden:
- `async with aiosqlite.connect(STATE_DB) as db:` für `upsert_user`.
- `async with aiosqlite.connect(CACHE_DB) as db:` für `save_course_index`.
- `async with aiosqlite.connect(TELEMETRY_DB) as db:` für `check_rate_limit`.

## 4. Bereinigungsprozesse (Garbage Collection)
Die Trennung erlaubt effizientere und sicherere Bereinigungsroutinen:
- **`cache.db`**: Beim Start (`init()`) werden alte Mensa-Gerichte (> 14 Tage) und abgelaufene `user_plan_cache`-Einträge gelöscht. Bei tiefgreifenden Änderungen am HKA-System kann die Datei vom Admin manuell gelöscht werden, ohne Nutzerdaten zu gefährden.
- **`telemetry.db`**: Beim Ausführen von `check_rate_limit` werden ohnehin alte `requests` (älter als 2 Stunden) gelöscht. Ein periodischer Full-Vacuum kann im Hintergrund-Task eingeplant werden.

## 5. Vorteile der neuen Architektur
1. **Zero-Downtime Backups:** `state.db` kann im laufenden Betrieb via SQLite Online-Backup API oder simplen Copy-Befehlen extrem schnell und ressourcenschonend gesichert werden, da sie klein bleibt.
2. **Erhöhter Durchsatz:** Da Telemetrie-Writes (Rate-Limit) nun in `telemetry.db` stattfinden, blockieren sie nicht länger die Lese-Zugriffe auf `cache.db` (z.B. wenn 10 Nutzer gleichzeitig ihren Stundenplan abfragen).
3. **Robuste Weiterentwicklung:** Neue Cache-Funktionen (z.B. für Gebäude-Pläne oder Dozenten) können unbesorgt in `cache.db` entwickelt und bei Schema-Fehlern hart resettet werden.

## 6. Nächste Schritte zur Implementierung
1. Erstellung eines Issue/Feature-Branches.
2. Anpassung der `src/db.py` gemäß dieser Spec.
3. Entwicklung und lokaler Test der Migrations-Logik (`bot.db` -> `state.db`).
4. Unit-Tests / Integrationstests ausführen, um sicherzustellen, dass alle Zugriffe korrekt auf die drei Säulen umgeleitet wurden.
