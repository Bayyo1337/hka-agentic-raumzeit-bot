# Verbesserung: Persistente Mensa-Datenbank

## Hintergrund & Motivation
Aktuell werden Mensa-Gerichte nur im RAM (`_MEALS_CACHE`) gespeichert. Dies führt dazu, dass nach einem Neustart des Bots oder wenn ein Nutzer direkt nach Allergenen fragt (ohne vorher das Menü gesehen zu haben), die Fehlermeldung "Gerichts-Details aktuell nur direkt nach der Speiseplan-Abfrage verfügbar" erscheint. Da der Speiseplan für einen Tag für alle Nutzer gleich ist, ist eine persistente Speicherung sinnvoll.

## Ursachenanalyse / Ist-Zustand
- Der Cache ist in `src/tools.py` als einfaches `dict` implementiert.
- Repro-Skript `scripts/repro_mensa_persistenz.py` zeigt: Nach dem Leeren der `dicts` ist kein Zugriff mehr möglich.

## Lösungsvorschlag
1. **Datenbank-Tabelle**: In der bestehenden `data/bot.db` eine neue Tabelle `mensa_meals` anlegen.
2. **Persistence-Layer**:
   - `save_mensa_meals(meals: list[dict])`: Speichert alle Gerichte eines Tages.
   - `get_mensa_meal(query_id_or_name: str)`: Sucht ein Gericht in der DB.
3. **Tool-Integration**:
   - `get_mensa_menu`: Ruft die API auf und persistiert das Ergebnis sofort.
   - `get_mensa_meal_details`: Nutzt erst den schnellen In-Memory-Cache und fällt dann auf die DB zurück.

## Umsetzungsschritte

### 1. `src/db.py` (Persistence)
- Tabelle `mensa_meals` definieren:
  ```sql
  CREATE TABLE IF NOT EXISTS mensa_meals (
      meal_id   TEXT PRIMARY KEY,
      name      TEXT NOT NULL,
      meal_json TEXT NOT NULL,
      date      TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_mensa_date ON mensa_meals(date);
  CREATE INDEX IF NOT EXISTS idx_mensa_name ON mensa_meals(name);
  ```
- Funktionen `save_mensa_meals` und `get_mensa_meal` implementieren.
- In `init()` automatisches Löschen alter Einträge (> 14 Tage).

### 2. `src/tools.py` (Logic)
- `get_mensa_menu`: Aufruf von `db.save_mensa_meals` am Ende der Verarbeitung.
- `get_mensa_meal_details`:
  - Erst In-Memory Check.
  - Dann `db.get_mensa_meal` Aufruf.
  - Beibehaltung der Fuzzy-Logik für manuelle Eingaben.

## Verifizierung & Testing
1. Ausführen des Repro-Skripts `scripts/repro_mensa_persistenz.py`. Nach dem Fix muss Schritt 4 Erfolg melden, da die Daten aus der DB geladen werden.
2. Manueller Test: `/mensa` aufrufen, Bot neu starten, dann Allergene zu einem Gericht von heute abfragen.
