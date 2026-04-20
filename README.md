# 🌌 HKA Raumzeit KI-Agent

Ein hochmoderner, autonomer KI-gestützter Telegram-Bot für Studierende der Hochschule Karlsruhe (HKA). Der Bot nutzt Large Language Models (LLMs) und ein spezialisiertes Agenten-System, um natürliche Sprache zu verstehen und präzise Informationen aus der Raumzeit-API, dem Mensa-Plan und den Personenverzeichnissen der HKA zu extrahieren.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![License](https://img.shields.io/badge/License-AGPL--3.0-red)
![Status](https://img.shields.io/badge/Status-Stabil-green)

---

## ✨ Hauptfunktionen & Features

### 🗣️ Intelligente Sprachverarbeitung (NLP)
Vergiss kryptische Befehle. Frag den Bot einfach alles rund um den Campus:
*   *"Wann ist Raum M-102 heute frei?"*
*   *"Zeig mir den Stundenplan von Maschinenbau Semester 2."*
*   *"Was unterrichtet Prof. Offermann am Donnerstag?"*
*   *"Welche Vorlesungen habe ich morgen?"* (erfordert Profil-Setup)
*   **NEU:** Ergebnisse werden nun immer **chronologisch korrekt** sortiert ausgegeben.

### 🎓 Personalisierung & Multi-Semester (`/setcourse`)
Der Bot merkt sich, was du studierst. Über einen interaktiven Assistenten kannst du:
*   **Mehrere Semester gleichzeitig** speichern (ideal für Wiederholer oder Wahlpflichtfächer).
*   Den Bot fragen: *"Was habe ich heute?"* – er filtert automatisch alle deine gespeicherten Kurse für den heutigen Tag.

### 🍴 Moderne Mensa-Integration (GraphQL)
Echtzeit-Abfrage der Speisepläne (Mensa Moltke und andere):
*   **Präzise Daten:** Vollständige Integration der neuen `api.mensa-ka.de` GraphQL-Schnittstelle.
*   **Details auf Klick:** Anzeige von Preisen (Student/Gast), Allergenen, Zusatzstoffen sowie veganer/vegetarischer Kennzeichnung.

### 🕒 Dozenten-Infos & Sprechzeiten
Nie wieder mühsam Profile suchen:
*   **Kontakt:** E-Mail-Adressen werden direkt angezeigt.
*   **Sprechzeiten:** Ein spezialisierter Scraper liest die aktuellen Sprechzeiten direkt von der HKA-Webseite aus.
*   **Namens-Auflösung:** Kürzel (z.B. `ofpe0001`) werden automatisch in Klarnamen aufgelöst.

### ⚠️ Stundenplan-Konflikt-Analyse
Ein mächtiges Werkzeug für die Semesterplanung:
*   **Befehl:** *"Finde Konflikte E-Technik im 2. Semester mit Vorlesungen aus dem 3. Semester"*
*   **Gruppen-Logik:** Der Bot prüft alle Gruppen-Suffixe (z.B. MABB.2.A vs MABB.3.B) und zeigt dir exakt an, welche Kombinationen zeitlich funktionieren.

### 📍 Intelligente Campus-Karten
Nie wieder den Raum suchen:
*   Bei Fragen nach Gebäuden oder Räumen sendet der Bot ein **dynamisch generiertes Bild**.
*   Das Zielgebäude wird exakt **rot markiert**.
*   Inklusive automatischer **Stockwerks-Info**.

### 🛠️ NEU: Admin-Power-Features
*   **Modularer Sync:** Mit `/sync courses` oder `/sync lecturers` gezielt nur Teile der Datenbank aktualisieren.
*   **Instant Issue Reporting:** Wenn ein technischer Fehler auftritt, können Admins diesen per Knopfdruck direkt als `active issue` in das Repository speichern – inkl. Traceback und Kontext.

---

## 🤖 Agentic Workflow & Development

Dieser Bot ist nicht nur eine Anwendung, sondern wird von einem Team spezialisierter KI-Agenten (Skills) entwickelt und gewartet. Im Verzeichnis `.gemini/skills/` befinden sich die Gehirne unserer autonomen Mitarbeiter:

*   **`strategist`**: Der Projektleiter. Er steuert die gesamte Kette von der Idee bis zum Git-Commit.
*   **`issue-planner`**: Analysiert Bugs und erstellt detaillierte Implementierungspläne.
*   **`issue-fixer`**: Setzt die Pläne methodisch im Quellcode um.
*   **`qa-reviewer`**: Validiert alle Änderungen, führt Tests durch und verwaltet die Git-Historie.
*   **`feature-planner`**: Wandelt grobe Ideen in technische Spezifikationen um.

---

## 🚀 Lokale Installation & Setup

Du kannst den Bot auf deinem eigenen Rechner oder Server laufen lassen. Wir nutzen das moderne Tool [uv](https://github.com/astral-sh/uv).

### 1. Voraussetzungen
*   **Python 3.11** oder neuer.
*   **uv** (installierbar via `curl -LsSf https://astral.sh/uv/install.sh | sh`).
*   Ein **Telegram Bot Token** (von [@BotFather](https://t.me/botfather)).
*   Ein **LLM API Key** (Empfohlen: Google Gemini, Claude, oder OpenAI).

### 2. Repository klonen & Setup
```bash
git clone https://github.com/Bayyo1337/hka-agentic-raumzeit-bot.git
cd hka-agentic-raumzeit-bot
uv sync
uv run python scripts/onboard.py
uv run python scripts/generate_maps.py
```

### 3. Bot starten
```bash
make run
```
*Tipp: Der Bot startet ein interaktives Dashboard im Terminal, in dem du Status, Log-Level und Token-Verbrauch in Echtzeit siehst.*

---

## 🛠️ Betrieb & Kommandos

### Telegram-Befehle (Admins)
*   `/sync [all|courses|lecturers]`: Gezielte Synchronisation der Datenquellen.
*   `/broadcast [nachricht]`: Sendet eine Nachricht an alle registrierten Nutzer.
*   `/loglevel [DEBUG|INFO|WARNING]`: Ändert die Detailtiefe der Logs zur Laufzeit.

### Telegram-Befehle (Nutzer)
*   `/setcourse`: Deinen Studiengang konfigurieren.
*   `/stats`: Deine persönliche Nutzungsstatistik einsehen.
*   `/reset`: Deinen Gesprächsverlauf löschen.

---

## 🧠 Architektur & Technologie

*   **Kern:** Asynchrones Python (APScheduler, Python-Telegram-Bot).
*   **KI:** [LiteLLM](https://github.com/BerriAI/litellm) zur Abstraktion verschiedener KI-Provider.
*   **Daten:** SQLite für Nutzerprofile und Cache; GraphQL & REST für HKA-Daten.
*   **UI:** [Rich](https://github.com/Textualize/rich) für das moderne Terminal-Dashboard.

Der Bot trennt strikt zwischen **Intent-Parsing** (Was will der Nutzer?) und **Execution** (Deterministic Python Code). Das sorgt für maximale Präzise und verhindert KI-Halluzinationen bei Terminen.

---
*Disclaimer: Dies ist ein inoffizielles Projekt und steht in keiner direkten Verbindung zur Verwaltung der Hochschule Karlsruhe.*
