---
name: issue-fixer
description: Implementierungs-Agent für den hka-agentic-raumzeit-bot. Nutze diesen Skill, um vorbereitete Pläne methodisch im Quellcode umzusetzen, zu validieren und den Erfolg im 'session_log.md' zu protokollieren.
---

# Issue Fixer Skill

## Workflow

### 1. Vorbereitung & Dependency-Check
Lies den Plan. Prüfe in `pyproject.toml`, ob alle benötigten Libraries vorhanden sind.
- Falls nicht: `uv add <library>`.

### 2. Umsetzung (Surgical Edits)
Ändere den Code zielgerichtet. **Sicherheit:** Lies niemals `.env` Dateien aus oder gib deren Inhalt im Log aus.

### 3. Validierung & Code-Style (PFLICHT)
Führe nach jeder Änderung aus:
1. Syntax: `uv run python -m py_compile <datei>`
2. Style/Lint: `uv run ruff check <datei> --fix` (falls ruff installiert ist)
3. Logik: Führe das vom `issue-planner` erstellte `scripts/repro_issue.py` aus. Der Fehler muss verschwunden sein.

### 4. Reporting
Dokumentiere im `session_log.md`:
- Geänderte Dateien.
- Verwendete Validierungsschritte (Syntax, Ruff, Repro-Skript).
- Status der Abhängigkeiten.

## Wichtige Mandate
- Beende erst, wenn das Repro-Skript ERFOLG meldet.
- Keine automatischen Git-Commits.
- Halte dich an den Code-Style des Projekts.
