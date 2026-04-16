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

### 👤 Dozenten-Details & Kontakte
Der Bot löst Dozenten-Kürzel automatisch in Klarnamen auf und bietet zusätzliche Informationen:
*   **Kontakt-Info:** E-Mail-Adressen und Sprechzeiten werden direkt von der HKA-Webseite geladen.
*   **Gezielte Abfrage:** *"Wie ist die E-Mail von Ahmadi?"* oder *"Wann hat Nils Ruf Sprechstunde?"*.

### 📍 Intelligente Campus-Karten
Nie wieder verlaufen! Bei Fragen nach Orten sendet der Bot:
*   Ein **final kalibriertes Bild** der Campus-Karte, auf dem das gesuchte Gebäude exakt rot eingekreist ist.
*   Automatische **Stockwerks-Erkennung** (z.B. *"Raum 145 liegt im 1. Stock"*).

### ❌ Stornierungs-Erkennung
Der Bot erkennt abgesagte Vorlesungen in der HKA-API und stellt diese in der Timeline deutlich **durchgestrichen** und mit einem ❌ markiert dar.

---

## 🛠️ Installation & Setup

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
    ```bash
    uv run python scripts/onboard.py
    ```

4.  **Karten generieren (einmalig):**
    ```bash
    uv run python scripts/generate_maps.py
    ```

---

## 🛡️ Stabilität & 24/7 Betrieb

Der Bot ist für den dauerhaften Einsatz auf Servern (LXC, Docker, Systemd) optimiert:
*   **Daemon-Modus:** Erkennt automatisch, wenn er im Hintergrund läuft, und passt das Logging an (kein Dashboard-Spam in `journalctl`).
*   **Nightly Sync:** Aktualisiert jede Nacht um 04:00 Uhr vollautomatisch alle Kurs- und Dozentendaten.
*   **Network Watchdog:** Erkennt dauerhafte Verbindungsabbrüche zu Telegram und erzwingt einen sauberen Neustart via Systemd.

---

## 💻 Betrieb

### Bot starten
```bash
make run
```

### Befehle im Terminal
*   `status`: Zeigt das interaktive Dashboard an (nur im Terminal-Modus).
*   `sync`: Manueller Abgleich mit der HKA-API.
*   `test run`: Führt die hinterlegten Stresstests aus.

### Befehle in Telegram
*   `/start` | `/help`: Einführung und Hilfe.
*   `/setcourse`: Dein Profil konfigurieren.
*   `/stats`: Nutzungsstatistik & Tokens.
*   `/togglemap` (Admin): Lagepläne an/aus schalten.

---

## 🧠 Architektur

Der Bot trennt strikt zwischen **Absichtserkennung** (LLM) und **Datenverarbeitung** (Python). Dies spart Kosten, erhöht die Geschwindigkeit und sorgt für 100% datenschutzkonforme API-Abfragen.

> **Hinweis für KI-Agenten:** Die Dateien `GEMINI.md` und `CLAUDE.md` enthalten spezifische Anweisungen für die Weiterentwicklung und sollten nur lokal verwendet werden.

---
*Entwickelt für die Studierenden der HKA.*
