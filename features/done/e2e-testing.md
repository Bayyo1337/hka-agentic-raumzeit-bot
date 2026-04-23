# Spezifikation: Automatisierte End-to-End (E2E) Test-Framework

## Zielsetzung
Das Ziel ist es, eine E2E-Testumgebung für den Raumzeit-KI-Agenten zu implementieren. Die Testumgebung soll sicherstellen, dass Anfragen, die in natürlicher Sprache formuliert sind, korrekt vom Router, dem LLM (Agent) und den Tools verarbeitet werden und dass eine ordentliche, markdowngerechte Antwort erzeugt wird. Auf diese Weise sollen Regressionen nach Feature-Änderungen automatisch verhindert werden.

## Technische Änderungen

### 1. Test-Fixtures anlegen
- **Datei:** `tests/fixtures/e2e_cases.json`
- **Beschreibung:** Eine JSON-Datei mit einem Array von Testfall-Objekten.
- **Datenstruktur (pro Fall):**
  - `name`: Eine kurze Beschreibung des Testfalls (z.B. "Einfache Raumabfrage").
  - `input`: Der Text, der in Telegram an den Bot gesendet würde (z.B. "Wann ist M-102 frei?").
  - `expected_intent`: Der erwartete Intent (z.B. `room_timetable`).
  - `expected_tools`: Ein Array von Tool-Namen, die vom Agenten zwingend aufgerufen werden müssen (z.B. `["get_room_timetable"]`).
  - `expected_keywords`: Ein Array von Wörtern, die zwingend in der finalen Bot-Antwort enthalten sein müssen.
  - `forbidden_keywords`: Ein Array von Wörtern, die *nicht* vorkommen dürfen (z.B. "Traceback", "Exception", "Fehler").

### 2. E2E Test Runner entwickeln
- **Datei:** `tests/test_e2e.py`
- **Beschreibung:** Ein pytest-Skript, das über `pytest.mark.parametrize` alle in der `e2e_cases.json` definierten Fälle testet.
- **Ablauf pro Testfall:**
  1. Ruft direkt die Methode `bot.handle_message` oder `agent.run` auf (oder simuliert das Telegram Update). Alternativ kann direkt der Aufruf von `agent.run()` mit vorab initialisierten Dummy-DBs ausgeführt werden. Da `agent.run` den Intent nun entgegennimmt, sollte das Skript zunächst `router_instance.classify_message` aufrufen, den Intent abgleichen und diesen dann an `agent.run` weitergeben.
  2. Überprüft, ob der von `router` zurückgegebene Intent dem `expected_intent` entspricht.
  3. Prüft, ob in den `collected_results` (die von `agent.run` zurückgegeben werden) die `expected_tools` aufgerufen wurden.
  4. Validiert, dass die generierte `reply`-Variable die `expected_keywords` enthält und keine der `forbidden_keywords`.

### 3. Makefile erweitern
- **Datei:** `Makefile`
- **Änderung:** Neues Target `test` oder `test-e2e` hinzufügen, welches das E2E-Testskript über `uv run pytest tests/` anstößt.

### 4. QA-Reviewer Skill anpassen
- **Datei:** `.gemini/skills/qa-reviewer/SKILL.md`
- **Änderung:** Den Schritt `make test` oder `uv run pytest` als zwingenden Check vor dem Git-Commit hinzufügen. Wenn ein Test fehlschlägt, darf der QA-Reviewer nicht committen.

## Datenmodell
- Es sind keine strukturellen Änderungen an den SQLite-Datenbanken (`state.db`, `cache.db`, `telemetry.db`) erforderlich. Die E2E-Tests sollten jedoch idealerweise eine In-Memory-Datenbank oder eine separate Test-DB (`DB_DIR="data/test_db"`) verwenden, um echte User-Daten und Rate Limits beim Testen nicht zu verfälschen.

## Test-Strategie
- Da das Framework selbst aus Tests besteht, ist die Validierung dieses Features abgeschlossen, sobald:
  1. Das Testskript fehlerfrei mit `pytest` läuft.
  2. Mindestens 5 Basis-Testfälle (Raum, Dozent, Mensa, Karte, Fallback) in der `e2e_cases.json` definiert sind.
  3. Ein absichtlich defekter Testfall korrekt erkannt wird (d.h. pytest schlägt fehl).