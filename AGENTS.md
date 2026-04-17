# 🤖 Autonome Agenten-Kette: Agentic Workflow

Dieses Repository ist für einen vollständig autonomen Entwicklungs-Workflow mit Gemini CLI optimiert. Anstatt manuelle Änderungen vorzunehmen, nutzt dieses System eine Kette von spezialisierten Agenten-Skills, die Probleme analysieren, lösen, validieren und committen.

## 🏗 Die Agenten-Rollen

| Agent | Skill-Name | Aufgabe |
| :--- | :--- | :--- |
| **Strategist** | `strategist` | **Der Manager.** Nimmt Prompts entgegen und steuert die gesamte Kette (Planner -> Fixer -> QA) autonom via CLI. |
| **Issue Planner** | `issue-planner` | **Der Analyst.** Untersucht den Code, erstellt einen Implementierungsplan (`problem.md`) und ein Repro-Skript. |
| **Issue Fixer** | `issue-fixer` | **Der Entwickler.** Setzt den Plan chirurgisch um, prüft die Syntax und validiert den Fix gegen das Repro-Skript. |
| **QA Reviewer** | `qa-reviewer` | **Der Qualitätswächter.** Prüft den Diff, führt finale Tests aus und committet die Änderungen sauber ins Git. |

## 🚀 Nutzung: "Fire and Forget"

Um einen Bug zu beheben oder ein Feature zu implementieren, reicht ein einziger Befehl:

```bash
gemini -i "BESCHREIBUNG DES PROBLEMS ODER WUNSCHES" --skill strategist
```

### Was passiert im Hintergrund?
1. Der **Strategist** initialisiert die Session.
2. Er ruft den **Planner** auf, um die Ursache zu finden.
3. Er ruft den **Fixer** auf, um den Code zu korrigieren.
4. Er ruft den **QA Reviewer** auf, um alles zu prüfen und zu committen.
5. Du erhältst am Ende eine Erfolgsmeldung inkl. Commit-Hash.

## 📂 Struktur & Artefakte (`.gemini/`)

- **`session_log.md`**: Die "Single Source of Truth". Hier protokollieren alle Agenten ihren Fortschritt und den Master-Plan.
- **`prompts/`**: Enthält die Analysen (`problem.md`, `verbesserung.md`) und die temporären Spezialisten-Prompts.
- **`skills/`**: Die Quellcodes der installierten Agenten-Skills.

## 📜 Mandate für Agenten
- **Empirische Beweislast:** Jeder Bug muss vor dem Fix durch ein Repro-Skript bewiesen werden.
- **Surgical Edits:** Nur die betroffenen Stellen ändern, kein unnötiges Refactoring.
- **Validation First:** Kein Commit ohne erfolgreiche Syntax- und Logikprüfung (`uv run python -m py_compile` & `ruff`).
- **Git Integrity:** Commits erfolgen nur durch den QA-Reviewer nach erfolgreichem Review.

---
*Status: Aktiviert am 17.04.2026. Bereit für autonome Entwicklung.*
