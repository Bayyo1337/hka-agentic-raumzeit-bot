# 🌌 HKA Raumzeit KI-Agent: Project State & Architecture

Dieses Dokument dient als technischer Kompass für KI-Agenten, die an diesem Repository arbeiten. Es beschreibt den aktuellen Stand (April 2026), die Architektur und die geltenden Mandate.

## 🏗 System-Architektur

Der Bot ist modular aufgebaut und trennt strikt zwischen API-Logik, KI-Verarbeitung und Telegram-Interface.

### Core Komponenten (`src/`)
- **`bot.py`**: Der Telegram-Einstiegspunkt. Verwaltet Handler, Callbacks und den interaktiven `/setcourse`-Assistenten.
- **`agent.py`**: Das Gehirn. Nutzt LiteLLM zur Intent-Extraktion. Wandelt natürliche Sprache in strukturierte Tool-Calls (JSON) um.
- **`tools.py`**: Die Schnittstelle zur Außenwelt. Implementiert Scraper/Wrapper für die HKA-Raumzeit-API und Campus-Karten.
- **`formatter.py`**: Wandelt rohe API-Daten in schönes Markdown für Telegram um. Beinhaltet radikale Normalisierung zur Event-Deduplizierung.
- **`db.py`**: SQLite-Backend (`data/bot.db`). Speichert Nutzerprofile, Token-Verbrauch, Verläufe und den Kurs-Index.
- **`admin.py`**: Logik für alle Admin-Befehle (`/sync`, `/ban`, `/broadcast`, `/loglevel`).
- **`terminal.py`**: Ein Rich-basiertes Dashboard und CLI für lokale Tests und Statusüberwachung.
- **`state.py`**: Globaler In-Memory State (Wartungsmodus, Feature-Toggles).
- **`config.py`**: Pydantic-basierte Konfiguration via `.env`.

## 🛠 Features (Stand: 11.04.2026)

1.  **KI-Intent Parsing**: Versteht Fragen wie "Wann ist M-102 frei?" oder "Was habe ich nächste Woche Dienstag?".
2.  **Personalisierung (`/setcourse`)**: Ein geführter Multi-Select Wizard erlaubt es Nutzern, mehrere Semester zu speichern. Der Bot antwortet dann kontextbezogen auf "Was habe ich heute?".
3.  **Intelligente Campus-Karten**: Bei Fragen nach Orten sendet der Bot automatisch ein hervorgehobenes Bild des Gebäudes (generiert aus `HKA_Lageplan_A4.pdf`) inkl. Stockwerks-Informationen.
4.  **Stornierungs-Erkennung**: Erkennt abgesagte Vorlesungen in der HKA-API und stellt diese im Timeline-View durchgestrichen dar.
5.  **Admin-Dashboard**: Echtzeit-Überwachung von Uptime, LLM-Provider und Log-Level im Terminal.
6.  **Sicherheit & Stabilität**:
    *   Sequentielles Stress-Testing (1s Delay) zur Vermeidung von 429-Fehlern (Mistral Free).
    *   Robuste Fehlerbehandlung für Telegram-Netzwerkfehler (kein Log-Spam).
    *   Automatischer Re-Build des Kurs-Index bei Veraltung.

## 📜 Wichtige Mandate & Regeln

- **Keine Mensa-Funktion**: Die Mensa-Integration wurde vollständig entfernt (Tools, Formatter und Agent-Wissen bereinigt).
- **Branch-Policy**: Alle Entwicklungen finden auf dem `gemini` Branch statt.
- **Syntax-Pflicht**: Nach jeder Änderung muss `uv run python -m py_compile [files]` ausgeführt werden.
- **Daten-Integrität**: Sensible Daten (`.env`, `data/*.db`, `data/test_runs/`) dürfen niemals committet werden (siehe `.gitignore`).
- **Normalisierung**: Event-Namen müssen vor dem Vergleich/Deduplizieren radikal normalisiert werden: `re.sub(r'[^a-z0-9]', '', s.lower())`.

## 🚀 Workflows

- **`/sync`**: Stößt den Abgleich von Kursen und Dozenten mit der HKA-API an.
- **`make run`**: Startet den Bot inkl. Dashboard.
- **Stundenplan-Abfrage**: Nutzt JSON-Mode (`/timetables/course/` etc.) mit `firstDate` für präzise Ergebnisse, da Text-Modi oft unvollständig sind.

---
*Status: Stabil. Bereit für Erweiterungen im Bereich Agentic-Workflows oder Analytics.*
