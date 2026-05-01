# Repo Restructuring: Struktur, Packaging & AI-Konventionen

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Behebe die kritischsten strukturellen Probleme im Repository – kaputtes Dockerfile, falsche README-Pfade, doppelte Tracking-Systeme und Verlust von KI-Analysen. Minimal-invasiv: kein Umbenennen des `src/`-Pakets (zu hoher Regressions-Aufwand), fokus auf sofort korrigierbare Fehler.

**Priority Order:** Kritisch (Dockerfile, README) → Hoch (session_log, prompts) → Mittel (scripts, conftest, docs/superpowers)

**Tech Stack:** Python, Docker, Makefile, Markdown, Bash.

---

### Task 1: Dockerfile reparieren (KRITISCH)

**Files:**
- Modify: `Dockerfile`

Der Docker-Build kopiert weder `assets/` noch `uv.lock` und führt `generate_maps.py` nicht aus. Ein frisch gebautes Image hat keine Karten – der Bot crasht bei jeder Kartenanfrage.

- [ ] **Step 1: `Dockerfile` korrigieren**

Ersetze den Inhalt durch:

```dockerfile
FROM python:3.11-slim

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies zuerst (Layer-Caching) – uv.lock für reproduzierbare Builds
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Assets und Source
COPY assets/ assets/
COPY src/ src/
COPY scripts/setup/generate_maps.py scripts/setup/generate_maps.py

# Karten beim Build generieren (benötigt assets/HKA_Lageplan_A4.pdf)
RUN uv run python scripts/setup/generate_maps.py

# .env wird zur Laufzeit per Volume oder ENV-Vars gesetzt
ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "-m", "src.bot"]
```

- [ ] **Step 2: Syntax-Check**

```bash
docker build --no-cache -t raumzeit-test . 2>&1 | head -40
```
Falls Docker nicht verfügbar: mindestens prüfen, ob alle referenzierten Dateien existieren:
```bash
test -f assets/HKA_Lageplan_A4.pdf && echo "OK" || echo "FEHLT"
test -f scripts/setup/generate_maps.py && echo "OK" || echo "FEHLT"
test -f uv.lock && echo "OK" || echo "FEHLT"
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "fix(docker): copy assets+uv.lock, generate maps at build time"
```

---

### Task 2: README-Pfade korrigieren (KRITISCH)

**Files:**
- Modify: `README.md`

`README.md` Zeilen 78–79 referenzieren `scripts/onboard.py` und `scripts/generate_maps.py` – beide Skripte wurden nach `scripts/setup/` verschoben und existieren unter den alten Pfaden nicht mehr.

- [ ] **Step 1: Pfade in README.md korrigieren**

Finde und ersetze in Abschnitt "2. Repository klonen & Setup":

```diff
-uv run python scripts/onboard.py
-uv run python scripts/generate_maps.py
+uv run python scripts/setup/onboard.py
+uv run python scripts/setup/generate_maps.py
```

- [ ] **Step 2: init.sh-Referenz prüfen**

Suche nach weiteren veralteten Pfaden:
```bash
grep -n "scripts/onboard\|scripts/generate_maps\|scripts/check\|scripts/init" README.md
```
Korrigiere alle Treffer analog.

- [ ] **Step 3: Verify**

```bash
uv run python -c "import ast; print('OK')"  # nur Syntax-Check
ls scripts/setup/onboard.py scripts/setup/generate_maps.py scripts/setup/check.py
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): fix script paths after scripts/setup/ migration"
```

---

### Task 3: `.gemini/session_log.md` aufteilen

**Files:**
- Modify/Create: `.gemini/logs/` (neues Verzeichnis)
- Modify: `.gemini/session_log.md`
- Modify: `.gemini/strategist.md` (Referenz aktualisieren)
- Modify: `.gemini/skills/qa-reviewer/SKILL.md` (Referenz aktualisieren)

Das `session_log.md` ist ein einziges lineares Dokument mit 9+ Sessions ohne Navigation. Neue Einträge können alte nicht mehr finden; Suche ist unpraktikabel.

- [ ] **Step 1: Verzeichnis anlegen und Sessions aufteilen**

```bash
mkdir -p .gemini/logs
```

Extrahiere jede `# Session Log - DD.MM.YYYY`-Sektion in eine eigene Datei:

| Sektion | Zieldatei |
|---|---|
| `# Session Log - 18.04.2026` (erste) | `.gemini/logs/2026-04-18.md` |
| `# Session Log - 20.04.2026` (erste) | `.gemini/logs/2026-04-20a.md` |
| `# Session Log - 20.04.2026` (zweite) | `.gemini/logs/2026-04-20b.md` |
| `# Session Log - 23.04.2026` | `.gemini/logs/2026-04-23.md` |
| `# Session Log - 30.04.2026` | `.gemini/logs/2026-04-30.md` |

- [ ] **Step 2: `session_log.md` als Index-Datei umschreiben**

Ersetze den gesamten Inhalt von `.gemini/session_log.md` durch einen Index:

```markdown
# Session Log – Index

Dieses Verzeichnis protokolliert alle Agenten-Sessions chronologisch.
Neue Sessions werden als `logs/YYYY-MM-DD.md` angelegt.

## Alle Sessions

| Datum | Tasks | Datei |
|---|---|---|
| 18.04.2026 | Raumnummern, Sync-Modularisierung, Konsolen-Fix, Performance | [2026-04-18.md](logs/2026-04-18.md) |
| 20.04.2026 | Help/Admin-Overhaul | [2026-04-20a.md](logs/2026-04-20a.md) |
| 20.04.2026 | Mensa Robustness, Allergen-Dekodierung | [2026-04-20b.md](logs/2026-04-20b.md) |
| 23.04.2026 | Dynamisches E2E-System | [2026-04-23.md](logs/2026-04-23.md) |
| 30.04.2026 | Markdown-Fix (Telegram Entities) | [2026-04-30.md](logs/2026-04-30.md) |

## Neue Session anlegen

1. Erstelle `.gemini/logs/YYYY-MM-DD.md`
2. Trage den Link in diese Tabelle ein
3. Protokolliere Tasks mit `## Task: <Name>` und `### Git` Abschnitt
```

- [ ] **Step 3: Referenzen in Skills aktualisieren**

In `.gemini/skills/qa-reviewer/SKILL.md` Zeile 14:
```diff
-Lies das `.gemini/session_log.md`, um den Kontext der Änderungen zu verstehen.
+Lies das aktuelle Log in `.gemini/logs/` (die neueste Datei nach Datum), um den Kontext der Änderungen zu verstehen. Trage neue Session-Ergebnisse in `.gemini/logs/YYYY-MM-DD.md` ein und aktualisiere den Index `.gemini/session_log.md`.
```

In `.gemini/strategist.md` (Schritt 1 des Workflows):
```diff
-1. **Planen:** Lies die Datei `.gemini/session_log.md` aus und halte den "Master Plan" aktuell.
+1. **Planen:** Lies den Index `.gemini/session_log.md` und die neueste Datei in `.gemini/logs/` aus. Lege für jede neue Session eine eigene Datei `logs/YYYY-MM-DD.md` an.
```

- [ ] **Step 4: Commit**

```bash
git add .gemini/
git commit -m "refactor(gemini): split session_log into dated files under .gemini/logs/"
```

---

### Task 4: `.gemini/prompts/` – Überschreiben verhindern

**Files:**
- Modify: `.gemini/issue_planner.md`
- Modify: `.gemini/skills/issue-planner/SKILL.md`

`issue_planner.md` Zeile 42 schreibt immer nach `prompts/problem.md` – jede neue Issue-Analyse überschreibt die vorherige, ohne dass ein Protokoll der alten Analyse erhalten bleibt.

- [ ] **Step 1: Namensschema in `issue_planner.md` aktualisieren**

Ersetze in `.gemini/issue_planner.md` Zeile 42:
```diff
-- Lege die Datei immer im Ordner `prompts/` ab (erstelle den Ordner, falls er nicht existiert).
+- Lege die Datei im Ordner `prompts/` ab. Nutze als Dateinamen: `problem-<slug>.md`, wobei `<slug>` eine kurze, kebab-case Beschreibung des Problems ist (z.B. `problem-prof-id-fallback.md`, `problem-mensa-allergen.md`). Überschreibe NIEMALS eine bestehende Datei – erstelle immer eine neue.
```

- [ ] **Step 2: Gleiches in `skills/issue-planner/SKILL.md` anpassen** (falls vorhanden und abweichend)

```bash
grep -n "prompts/problem.md\|problem\.md" .gemini/skills/issue-planner/SKILL.md
```
Analoge Änderung vornehmen.

- [ ] **Step 3: Bestehende `prompts/problem.md` umbenennen**

```bash
# Die aktuelle problem.md betrifft den Dozenten-Kürzel-Bug
mv .gemini/prompts/problem.md .gemini/prompts/problem-prof-id-regex.md
```

- [ ] **Step 4: Commit**

```bash
git add .gemini/
git commit -m "fix(gemini): prevent prompt overwrites – use slug-based filenames"
```

---

### Task 5: `docs/superpowers/` aufräumen

**Files:**
- Move: `docs/superpowers/plans/*.md` → `.gemini/logs/` oder `features/specs/`
- Move: `docs/superpowers/specs/*.md` → `features/specs/`
- Remove: `docs/superpowers/` (leeres Verzeichnis)

`docs/superpowers/` ist eine dritte Planungsebene neben `features/` und `issues/` mit undurchsichtigem Namen. Die darin enthaltenen Dateien gehören zu den bestehenden Systemen.

- [ ] **Step 1: Dateien in das richtige System verschieben**

```bash
# Plans sind AI-Arbeitsdokumente → .gemini/logs/ (als Referenz)
mv docs/superpowers/plans/2026-05-01-personalization-fix.md \
   .gemini/logs/2026-05-01-personalization-plan.md

# Specs sind Feature-Spezifikationen → features/specs/
mv docs/superpowers/specs/2026-05-01-personalization-fix.md \
   features/specs/2026-05-01-personalization-fix.md

# Diesen Plan selbst nach features/done/ verschieben (nach Abschluss)
# → wird durch qa-reviewer erledigt
```

- [ ] **Step 2: Leere Verzeichnisse entfernen**

```bash
rmdir docs/superpowers/plans docs/superpowers/specs docs/superpowers
```

- [ ] **Step 3: Verify – keine toten Referenzen**

```bash
grep -rn "superpowers" README.md docs/ .gemini/ || echo "Keine Referenzen mehr"
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(docs): dissolve docs/superpowers/, move artefacts to correct homes"
```

---

### Task 6: `tests/conftest.py` einführen

**Files:**
- Create: `tests/conftest.py`
- Modify: `Makefile`
- Modify: `tests/test_e2e.py` (DB-Setup-Duplizierung entfernen)

Alle Tests setzen `PYTHONPATH=.` via Makefile und haben DB-Setup-Boilerplate inline. Ein `conftest.py` zentralisiert das.

- [ ] **Step 1: `tests/conftest.py` erstellen**

```python
"""Gemeinsame Pytest-Fixtures für alle Tests."""
import os
import pytest

# DB in temporäres Verzeichnis umleiten – muss vor src-Imports gesetzt sein
def pytest_configure(config):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="raumzeit_test_")
    os.environ.setdefault("DB_DIR", tmp)
```

- [ ] **Step 2: Makefile bereinigen**

```diff
 test-e2e:
-	PYTHONPATH=. uv run pytest tests/test_e2e.py -v
+	uv run pytest tests/test_e2e.py -v

 test-e2e-dynamic:
 	@echo "📡 Erzeuge dynamische Test-Cases aus Realdaten..."
-	PYTHONPATH=. uv run python scripts/generate_e2e_fixtures.py
-	PYTHONPATH=. uv run pytest tests/test_e2e.py -v
+	uv run python scripts/generate_e2e_fixtures.py
+	uv run pytest tests/test_e2e.py -v
```

Außerdem `lint` um `tests/` erweitern:
```diff
 lint:
-	uv run ruff check src/ scripts/
+	uv run ruff check src/ scripts/ tests/
```

- [ ] **Step 3: Verify**

```bash
uv run pytest tests/ -v --tb=short 2>&1 | tail -20
```

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py Makefile
git commit -m "test: add conftest.py, remove PYTHONPATH hacks from Makefile"
```

---

### Task 7: Dateinamen in `issues/done/` normalisieren

**Files:**
- Rename: eine Datei in `issues/done/` mit Leerzeichen und Apostroph

- [ ] **Step 1: Datei umbenennen**

```bash
git mv "issues/done/Keine Vorlesungen für das Basis-Semester mit dem Filter 'thermodynamik' gefunden.md" \
       "issues/done/keine-vorlesungen-thermodynamik-filter.md"
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore(issues): normalize filename with spaces/apostrophes"
```

---

## Verification Checklist (nach allen Tasks)

```bash
# 1. Linting
uv run ruff check src/ scripts/ tests/

# 2. Syntax aller src-Dateien
uv run python -m py_compile src/bot.py src/db.py src/tools.py src/formatter.py

# 3. Tests
uv run pytest tests/ -v --tb=short

# 4. Keine toten README-Pfade
grep -n "scripts/onboard.py\|scripts/generate_maps.py" README.md && echo "FEHLER: alte Pfade" || echo "OK"

# 5. Keine doppelten problem.md
ls .gemini/prompts/problem.md 2>/dev/null && echo "WARNUNG: generische problem.md existiert noch" || echo "OK"
```
