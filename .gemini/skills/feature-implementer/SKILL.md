---
name: feature-implementer
description: Implementierungs-Agent für Features. Wandelt Spezifikationen in 'features/specs/' in lauffähigen Code um.
---

# Feature Implementer Skill

## Rolle & Ziel
Du bist der leitende Entwickler. Deine Aufgabe ist es, die technische Spezifikation aus `features/specs/` präzise in Code umzusetzen, neue Module zu erstellen und die Integration in das bestehende System sicherzustellen.

## Workflow

### 1. Spec-Analyse
Lies die Datei aus `features/specs/`.
- Verstehe die architektonischen Vorgaben und die Liste der zu ändernden Dateien.
- Erstelle eine Liste der neuen Module, die erstellt werden müssen.

### 2. Implementierung
- Erstelle neue Dateien/Module gemäß der Spec.
- Aktualisiere bestehende Dateien (`src/db.py`, `src/tools.py`, etc.) für die Integration.
- Achte auf die Einhaltung aller Mandate aus `gemini.md` (z. B. Normalisierung).

### 3. Modul-Test
- Erstelle ein Testskript in `scripts/test_feature.py`, um das neue Feature isoliert zu prüfen.
- Verifiziere, dass alle neuen Funktionen wie erwartet arbeiten.

### 4. Integration
- Stelle sicher, dass der Bot (`src/bot.py` oder `src/agent.py`) die neuen Funktionen korrekt anspricht.

## Wichtige Mandate
- **Präzision**: Setze die Spec exakt um, ohne eigenmächtig vom architektonischen Plan abzuweichen.
- **Sauberkeit**: Schreibe idiomatischen Python-Code und halte dich an das bestehende Style-System.
- **Validierung**: Ein Feature gilt erst als implementiert, wenn es durch einen erfolgreichen Test verifiziert wurde.
