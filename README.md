# 🌌 HKA Raumzeit KI-Agent

Ein hochmoderner Telegram-Bot für Studierende der Hochschule Karlsruhe (HKA). Er nutzt Large Language Models (LLMs), um natürliche Sprache in präzise Abfragen für die offizielle Raumzeit-API zu übersetzen.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![Status](https://img.shields.io/badge/Status-Stabil-green)

---

## ✨ Hauptfunktionen

### 🗣️ Natürliche Sprachverarbeitung
Frag den Bot einfach so, wie du einen Kommilitonen fragen würdest:
*   *"Wann ist M-102 heute frei?"*
*   *"Was unterrichtet Dietmar Feßler am Freitag?"*
*   *"Wo ist der Raum LI-145?"*
*   *"Was habe ich nächste Woche Dienstag?"*

### 🎓 Personalisierung (`/setcourse`)
Ein intelligenter, geführter Multi-Step-Assistent erlaubt es dir, deinen eigenen Studiengang zu hinterlegen:
*   **Multi-Select:** Speichere mehrere Semester gleichzeitig (z.B. aus dem 3. und 6. Semester).
*   **Intelligenter Kontext:** Einmal eingestellt, weiß der Bot bei Fragen wie *"Was habe ich heute?"* automatisch, welcher Stundenplan gemeint ist.
*   **Automatische Aggregation:** Bei Auswahl eines Hauptkurses (z.B. `MABB.7`) werden automatisch alle Untervarianten (`MABB.7DF`, `MABB.7.A` etc.) kombiniert.

### 📍 Intelligente Campus-Karten
Nie wieder verlaufen! Bei Fragen nach Orten sendet der Bot:
*   Ein **hervorgehobenes Bild** der Campus-Karte, auf dem das gesuchte Gebäude rot eingekreist ist.
*   Automatische **Stockwerks-Erkennung** (z.B. *"Raum 145 liegt im 1. Stock"*).

### ❌ Stornierungs-Erkennung
Der Bot erkennt abgesagte Vorlesungen in der HKA-API und stellt diese in der Timeline deutlich **durchgestrichen** und mit einem ❌ markiert dar.

### 📊 Admin Dashboard & CLI
Für Betreiber bietet der Bot eine leistungsstarke Terminal-Oberfläche:
*   **Live-Statistiken:** Echtzeit-Anzeige von Uptime, LLM-Provider und Log-Level.
*   **Interaktive Konsole:** Steuerung via Terminal (`status`, `sync`, `loglevel`).
*   **Stresstest-Tool:** Integriertes Tool zur Simulation von parallelen Nutzeranfragen inklusive automatischer Speicherung der Ergebnisse.

---

## 🚀 Installation & Setup

Wir empfehlen die Nutzung von [uv](https://github.com/astral-sh/uv).

1.  **Repository klonen:**
    ```bash
    git clone https://github.com/Bayyo1337/hka-agentic-raumzeit-bot.git
    cd hka-agentic-raumzeit-bot
    ```

2.  **Abhängigkeiten installieren:**
    ```bash
    uv sync
    ```

3.  **Konfiguration (Onboarding):**
    Starte den interaktiven Assistenten, um deine `.env` Datei zu erstellen:
    ```bash
    uv run python scripts/onboard.py
    ```

4.  **Karten generieren (einmalig):**
    ```bash
    uv run python scripts/generate_maps.py
    ```

---

## 🛠️ Betrieb

### Bot starten
```bash
make run
```

### Befehle im Terminal
*   `status`: Zeigt das Dashboard an.
*   `sync`: Synchronisiert Kurse und Dozenten mit der HKA-API.
*   `test run`: Führt die hinterlegten Stresstests aus.
*   `loglevel debug|info`: Ändert die Detailtiefe der Logs zur Laufzeit.

### Befehle in Telegram
*   `/start`: Einführung und Kurzhilfe.
*   `/help`: Ausführliche Hilfe mit Beispielen.
*   `/setcourse`: Deinen eigenen Stundenplan konfigurieren.
*   `/stats`: Deine persönliche Nutzungsstatistik.

---

## 🧠 Architektur

Der Bot trennt strikt zwischen **Absichtserkennung** und **Datenverarbeitung**:
1.  **Intent-Extraction:** Das LLM parst die Nutzernachricht und gibt strukturiertes JSON zurück.
2.  **Python-Execution:** Der Bot führt die API-Aufrufe asynchron und ggf. parallel aus.
3.  **Smarte Formatierung:** Die Antwort wird rein in Python formatiert (spart Tokens und ist schneller).
4.  **Caching:** JWT-Token und API-Abfragen werden intelligent gecacht, um die Last auf die HKA-Server zu minimieren.

---
*Entwickelt für die Studierenden der HKA. Datenschutz steht an erster Stelle: Keine Speicherung von Passwörtern im Repository.*
