# 🌌 HKA Raumzeit KI-Agent

Ein hochmoderner, KI-gestützter Telegram-Bot für Studierende der Hochschule Karlsruhe (HKA). Der Bot nutzt Large Language Models (LLMs), um natürliche Sprache zu verstehen und präzise Informationen aus der Raumzeit-API, dem Mensa-Plan und den Personenverzeichnissen der HKA zu extrahieren.

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

### 🎓 Personalisierung & Multi-Semester (`/setcourse`)
Der Bot merkt sich, was du studierst. Über einen interaktiven Assistenten kannst du:
*   **Mehrere Semester gleichzeitig** speichern (ideal für Wiederholer oder Wahlpflichtfächer).
*   Den Bot fragen: *"Was habe ich heute?"* – er filtert automatisch alle deine gespeicherten Kurse für den heutigen Tag.

### 🍴 Moderne Mensa-Integration (GraphQL)
Echtzeit-Abfrage der Speisepläne (Mensa Moltke und andere):
*   **Präzise Daten:** Vollständige Integration der neuen `api.mensa-ka.de` GraphQL-Schnittstelle.
*   **Details auf Klick:** Anzeige von Preisen (Student/Gast), Allergenen, Zusatzstoffen sowie veganer/vegetarischer Kennzeichnung.
*   **Intelligenz:** Erkennt automatisch, wenn die Mensa geschlossen ist oder keine Pläne vorliegen.

### 🕒 Dozenten-Infos & Sprechzeiten
Nie wieder mühsam Profile suchen:
*   **Kontakt:** E-Mail-Adressen werden direkt angezeigt.
*   **Sprechzeiten:** Ein spezialisierter Scraper liest die aktuellen Sprechzeiten/Sprechstunden direkt von der HKA-Webseite aus.
*   **Namens-Auflösung:** Kürzel (z.B. `ofpe0001`) werden automatisch in Klarnamen aufgelöst.

### ⚠️ NEU: Stundenplan-Konflikt-Analyse
Ein mächtiges Werkzeug für die Semesterplanung:
*   **Befehl:** *"Finde Konflikte E-Technik im 2. Semester mit Vorlesungen aus dem 3. Semester"*
*   **Gruppen-Logik:** Der Bot prüft alle Gruppen-Suffixe (z.B. MABB.2.A vs MABB.3.B) und zeigt dir exakt an, welche Kombinationen zeitlich funktionieren und welche nicht.

### 📍 Intelligente Campus-Karten
Nie wieder den Raum suchen:
*   Bei Fragen nach Gebäuden oder Räumen sendet der Bot ein **dynamisch generiertes Bild**.
*   Das Zielgebäude wird exakt **rot markiert**.
*   Inklusive automatischer **Stockwerks-Info** (z.B. *"Raum 145 befindet sich im 1. OG"*).

---

## 🚀 Lokale Installation & Setup

Du kannst den Bot auf deinem eigenen Rechner oder Server laufen lassen. Wir nutzen das moderne Tool [uv](https://github.com/astral-sh/uv) für blitzschnelles Dependency-Management.

### 1. Voraussetzungen
*   **Python 3.11** oder neuer.
*   **uv** (installierbar via `curl -LsSf https://astral.sh/uv/install.sh | sh`).
*   Ein **Telegram Bot Token** (von [@BotFather](https://t.me/botfather)).
*   Ein **LLM API Key** (Empfohlen: Google Gemini (kostenlos), Claude, oder OpenAI).

### 2. Repository klonen
```bash
git clone https://github.com/Bayyo1337/hka-agentic-raumzeit-bot.git
cd hka-agentic-raumzeit-bot
```

### 3. Abhängigkeiten installieren
```bash
uv sync
```

### 4. Konfiguration (`.env`)
Starte den interaktiven Onboarding-Assistenten, der die `.env` Datei für dich erstellt:
```bash
uv run python scripts/onboard.py
```
Alternativ kopiere die `.env.example` und fülle sie manuell aus.

### 5. Karten-Material generieren
Damit die intelligenten Karten funktionieren, muss das PDF einmalig in Bilder umgewandelt werden:
```bash
uv run python scripts/generate_maps.py
```

### 6. Bot starten
```bash
make run
```
*Tipp: Der Bot startet ein interaktives Dashboard im Terminal, in dem du Status, Log-Level und Token-Verbrauch in Echtzeit siehst.*

---

## 🛠️ Betrieb & Kommandos

### Terminal-Konsole
Wenn der Bot läuft, kannst du im Terminal Befehle eingeben:
*   `status`: Zeigt das Dashboard erneut an.
*   `sync`: Erzwingt einen sofortigen Neu-Abgleich aller Kurs- und Dozenten-Daten.
*   `loglevel DEBUG`: Schaltet ausführliches Logging ein.

### Telegram-Befehle
*   `/start`: Begrüßung und erste Schritte.
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
