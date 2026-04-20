# Plan: Datenbank-Refactoring & Robuste Mensa-ID-Auflösung

## Hintergrund & Motivation
1. Nutzer wünscht eine **getrennte Datenbank** für Mensa-Caches ("eigene Datenbank"). Dies deckt sich mit der geplanten Aufteilung in `state.db`, `cache.db` und `telemetry.db`.
2. Die Allergen-Abfrage schlägt oft fehl, weil das LLM **ID-Muster rät** (z.B. `gut_günstig_1`), anstatt UUIDs oder Namen zu verwenden.
3. Der Nutzer sieht (möglicherweise durch veraltete Prozesse) noch alte Fehlermeldungen.

## Ursachenanalyse / Ist-Zustand
- **DB-Struktur**: Aktuell alles in `bot.db`.
- **ID-Auflösung**: `get_mensa_meal_details` nutzt UUID-Match, Substring-Match und Fuzzy-Match auf dem Namen. Es erkennt keine strukturellen Muster wie `Kategorie_N`.
- **LLM-Verhalten**: In `allergen-abfrage.md` sieht man, dass das LLM `gut_günstig_1` generiert, wenn es den Seelachs meint.

## Lösungsvorschlag

### 1. Datenbank-Splittung (Refactoring)
- Umbau von `src/db.py` gemäß `database-split.md`.
- `state.db`: User, History, Tokens.
- `cache.db`: Kurs-Index, **Mensa-Meals**, Plan-Cache.
- `telemetry.db`: Rate-Limit-Logs.
- Automatischer Migrationspfad von `bot.db` -> `state.db` (Drop Caches).

### 2. Robuste Mensa-ID-Auflösung (Logic Fix)
- In `get_mensa_meal_details` ein **Spezial-Fallback** für Muster wie `gut_günstig_1` oder `wahlessen_2_3` einbauen.
- Logik:
  - Wenn ID auf `_[0-9]+` endet:
    - Lade alle Gerichte von heute aus `cache.db`.
    - Gruppiere nach Kategorie (Aktionstheke, Buffet, Gut & Günstig, Wahlessen 1, Wahlessen 2).
    - Mappe die geratene Kategorie auf die reale Kategorie (z.B. `gut_guenstig` -> `Gut & Günstig`).
    - Nimm das N-te Gericht dieser Liste.
- **WICHTIG**: Tool-Description anpassen, um dem LLM zu sagen, dass es Namen verwenden SOLLTE.

## Umsetzungsschritte

1. **`src/db.py`**:
   - Pfad-Konstanten für die drei DBs definieren.
   - `init()`-Logik aufteilen und Migrations-Check einbauen.
   - Alle Funktionen (ca. 20) auf die richtige DB-Verbindung umstellen.
2. **`src/tools.py`**:
   - `get_mensa_meal_details` erweitern um Kategorien-Lookup.
   - `TOOL_DEFINITIONS` für Mensa anpassen.
3. **`src/agent.py`**:
   - (Optional) System-Prompt schärfen für ID-Extraktion.

## Verifizierung & Testing
1. Ausführen von `scripts/repro_id_guessing.py`. Es MUSS nun Erfolg melden bei `gut_günstig_1`.
2. Vollständiger `uv run python -m py_compile` Check.
3. Neustart-Check: Sicherstellen, dass die Caches in `cache.db` persistiert werden.
