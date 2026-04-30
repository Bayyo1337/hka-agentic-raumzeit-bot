# Spec: Dynamisches E2E-Testsystem & Cache-Isolation

## Zielsetzung
Die E2E-Tests sollen hochpräzise gegen den **tagesaktuellen Speiseplan** validieren, anstatt generische Keywords zu nutzen. Gleichzeitig muss sichergestellt werden, dass die **Auto-Warming-Logik** (automatisches Nachladen bei leerem Cache) bei jedem Testlauf erzwungen wird, um Regressionen im Kaltstart-Verhalten zu verhindern.

## Technische Änderungen

### 1. `src/db.py` (Datenbank-Erweiterung)
- Implementierung einer Funktion `async def clear_mensa_cache() -> None`.
- Diese Funktion löscht alle Einträge aus der Tabelle `mensa_meals` in der `CACHE_DB`.
- Zweck: Ermöglicht es der Test-Suite, einen Kaltstart zu erzwingen.

### 2. `scripts/generate_e2e_fixtures.py` (Neues Modul)
- Dieses Skript wird vor den E2E-Tests ausgeführt.
- **Logik**:
  - Ruft die Mensa-API (`tools.get_mensa_menu`) auf.
  - Extrahiert die Namen der ersten 3 Gerichte und deren Linien.
  - Liest die bestehende `tests/fixtures/e2e_cases.json`.
  - Aktualisiert die "Allergene"-Testcases mit den **echten Namen** der Gerichte des Tages.
  - Speichert das Ergebnis als `tests/fixtures/dynamic_e2e_cases.json`.

### 3. `tests/test_e2e.py` (Suite-Anpassung)
- **Setup**: In `setup_test_db` wird `await db.clear_mensa_cache()` aufgerufen.
- **Fixture**: Die Suite lädt nun standardmäßig `dynamic_e2e_cases.json`, falls vorhanden (Fallback auf statische Cases).

### 4. `Makefile`
- Neuer Target `test-e2e-dynamic`:
  ```makefile
  test-e2e-dynamic:
      uv run python scripts/generate_e2e_fixtures.py
      PYTHONPATH=. uv run pytest tests/test_e2e.py -v
  ```

### 5. `.gemini/skills/qa-reviewer/SKILL.md`
- Aktualisierung des Workflows: Der `qa-reviewer` muss nun `make test-e2e-dynamic` nutzen, um die volle Präzision zu gewährleisten.

## Datenmodell
Es wird keine neue permanente Datenbank benötigt, da wir die bestehende `CACHE_DB` für die Isolation leeren und eine temporäre JSON-Fixture für die Dynamik nutzen.

## Test-Strategie
1. Ausführen von `make test-e2e-dynamic`.
2. Verifizierung im Log:
   - "Mensa-Cache leer für heute. Starte Auto-Warming..." muss im Log erscheinen (Beweis für Isolation).
   - Die Tests müssen gegen die echten Gerichtsnamen (z.B. "Putenschnitzel") grünes Licht geben.
