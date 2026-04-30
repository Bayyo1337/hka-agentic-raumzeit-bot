# 🌌 HKA Raumzeit KI-Agent

Ein hochmoderner, autonomer KI-gestützter Telegram-Bot für Studierende der Hochschule Karlsruhe (HKA). Der Bot nutzt Large Language Models (LLMs) und ein spezialisiertes Multi-Agenten-System, um natürliche Sprache zu verstehen und präzise Informationen aus der Raumzeit-API, dem Mensa-Plan und den Personenverzeichnissen der HKA zu extrahieren.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![License](https://img.shields.io/badge/License-AGPL--3.0-red)
![Status](https://img.shields.io/badge/Status-Stabil-green)

---

## ✨ Hauptfunktionen & Features

### 🗣️ Intelligente Sprachverarbeitung (NLP)
Vergiss kryptische Befehle. Durch ein hybrides **Intent-Routing** (Kombination aus schnellen Heuristiken und LLM-Präzision) versteht der Bot deine Fragen sofort:
*   *"Wann ist Raum M-102 heute frei?"*
*   *"Zeig mir den Stundenplan von Maschinenbau Semester 2."*
*   *"Was unterrichtet Prof. Offermann am Donnerstag?"*
*   *"Welche Vorlesungen habe ich morgen?"* (erfordert Profil-Setup)
*   **Performance:** Häufige Anfragen (wie Konflikt-Analysen) werden über Fast-Path-Heuristiken blitzschnell ohne LLM-Verzögerung verarbeitet.

### 🎓 Personalisierung & Multi-Semester (`/setcourse`)
Der Bot merkt sich, was du studierst. Über einen interaktiven Assistenten kannst du:
*   **Mehrere Semester gleichzeitig** speichern (ideal für Wiederholer oder Wahlpflichtfächer).
*   Den Bot fragen: *"Was habe ich heute?"* – er filtert automatisch alle deine gespeicherten Kurse für den heutigen Tag.

### 🍴 Moderne Mensa-Integration (GraphQL)
Echtzeit-Abfrage der Speisepläne (Mensa Moltke und andere):
*   **Präzise Daten:** Vollständige Integration der neuen `api.mensa-ka.de` GraphQL-Schnittstelle.
*   **Details auf Klick:** Anzeige von Preisen (Student/Gast), Allergenen, Zusatzstoffen sowie veganer/vegetarischer Kennzeichnung.
*   **Robustheit:** Intelligente ID-Verarbeitung verhindert Fehler bei halluzinierten Datums-Suffixen.

### ⚠️ Stundenplan-Konflikt-Analyse
Ein mächtiges Werkzeug für die Semesterplanung:
*   **Befehl:** *"Finde Konflikte E-Technik im 2. Semester mit Vorlesungen aus dem 3. Semester"*
*   **Intelligente Filter:** Der Bot erkennt automatisch, ob er nach Modulen filtern muss oder den gesamten Plan vergleicht.
*   **Gruppen-Logik:** Exakte Prüfung aller Gruppen-Suffixe (z.B. MABB.2.A vs MABB.3.B).

### 📍 Intelligente Campus-Karten
Nie wieder den Raum suchen:
*   Bei Fragen nach Gebäuden oder Räumen sendet der Bot ein **dynamisch generiertes Bild**.
*   Das Zielgebäude wird exakt **rot markiert** (basierend auf dem offiziellen Lageplan).
*   Inklusive automatischer **Stockwerks-Info**.

### 🛡️ Stabilität & Sicherheit
*   **Markdown Safety:** Globales Escaping aller API-Daten verhindert Telegram-Abstürze ("Can't find end of the entity").
*   **Fehler-Resistenz:** Robuste Behandlung von Netzwerkfehlern und automatische Re-Builds veralteter Indizes.

---

## 🤖 Agentic Workflow & Development

Dieses Projekt wird von einem Team spezialisierter KI-Agenten (Skills) entwickelt. Diese arbeiten autonom nach dem Prinzip **Research -> Strategy -> Execution**:

*   **`strategist`**: Der Projektleiter. Orchestriert die Kette von der Idee bis zum Git-Commit.
*   **`issue-planner`**: Analysiert Probleme und erstellt detaillierte Architektur-Pläne.
*   **`issue-fixer`**: Implementiert die Lösungen methodisch im Quellcode.
*   **`feature-planner`**: Konzipiert neue Features und erstellt technische Spezifikationen.
*   **`feature-implementer`**: Setzt Spezifikationen in sauberen, lauffähigen Code um.
*   **`qa-reviewer`**: Unabhängige Qualitätskontrolle, führt Tests durch und verwaltet die Git-Historie.

---

## 🚀 Lokale Installation & Setup

Wir nutzen [uv](https://github.com/astral-sh/uv) für blitzschnelles Dependency-Management.

### 1. Voraussetzungen
*   **Python 3.11** oder neuer.
*   **uv** (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
*   **Telegram Bot Token** ([@BotFather](https://t.me/botfather)).
*   **LLM API Key** (Google Gemini, Claude, oder OpenAI via LiteLLM).

### 2. Repository klonen & Setup
```bash
git clone https://github.com/Bayyo1337/hka-agentic-raumzeit-bot.git
cd hka-agentic-raumzeit-bot
uv sync
uv run python scripts/onboard.py
uv run python scripts/generate_maps.py
```

### 3. Testing & Start
```bash
# Validierung der Umgebung
make test-e2e-dynamic

# Bot starten
make run
```

---

## 🧠 Architektur & Technologie

*   **Daten-Pfeiler (3-Pillar DB):** 
    *   `state.db`: Nutzerprofile, Einstellungen und Session-States.
    *   `cache.db`: Hochperformante Caches für Raumzeit- und Mensa-Daten.
    *   `telemetry.db`: Detaillierte Logs und Token-Verbrauchs-Metriken.
*   **Kern:** Asynchrones Python (APScheduler, Python-Telegram-Bot).
*   **KI:** [LiteLLM](https://github.com/BerriAI/litellm) zur Abstraktion verschiedener Provider.
*   **UI:** Modernes [Rich](https://github.com/Textualize/rich) Terminal-Dashboard für Echtzeit-Monitoring.

Der Bot trennt strikt zwischen **Intent-Parsing** (Erkennung des Nutzerwunschs) und **Execution** (deterministischer Python-Code), um Halluzinationen bei Fakten auszuschließen.

---
*Disclaimer: Dies ist ein inoffizielles Projekt und steht in keiner direkten Verbindung zur Verwaltung der Hochschule Karlsruhe.*
