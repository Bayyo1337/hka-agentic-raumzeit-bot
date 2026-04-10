# Raumzeit KI-Agent (HKA) 🚀

Ein intelligenter Telegram-Bot für die Hochschule Karlsruhe (HKA), der natürliche Sprache nutzt, um Fragen zum Stundenplan, Raumbelegungen und Dozenten blitzschnell und präzise zu beantworten. Angetrieben von LLMs (Mistral, Gemini, Claude, Groq) und der offiziellen Raumzeit-API.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![Status](https://img.shields.io/badge/Status-Beta-orange)

---

## ✨ Features

- **🗣️ Natürliche Sprache:** Frag einfach: *"Wann ist M-102 nächste Woche Dienstag frei?"* oder *"Wo hat Udo Eichinger heute Vorlesung?"*.
- **⚡ Blitzschnell:** Das KI-Modell extrahiert nur die *Absicht (Intent)*. Die eigentlichen API-Abfragen und das Formatieren der Antwort übernimmt effizienter Python-Code.
- **🏫 Raum-Timeline:** Belegungen und freie Slots (🟢/🔴) werden als übersichtlicher Zeitstrahl direkt in Telegram dargestellt – inklusive Modulnamen und Dozenten.
- **📊 Live Dashboard:** Ein farbiges, interaktives Terminal-Dashboard (`rich`) zeigt dir Uptime, Logs und Systemstatus in Echtzeit.
- **🔐 Sicher:** Sensible Daten (API-Keys, HKA-Login) bleiben lokal in der `.env` und werden niemals ins Repo gepusht.

## 🛠️ Installation & Onboarding

Wir nutzen [uv](https://github.com/astral-sh/uv) als rasend schnellen Python Package Manager.

1. **Repository klonen**
   ```bash
   git clone https://github.com/DeinName/hka-agentic-raumzeit-bot.git
   cd hka-agentic-raumzeit-bot
   ```

2. **Abhängigkeiten installieren**
   ```bash
   uv sync
   ```

3. **Interaktives Onboarding (Setup-Assistent)**
   Wir haben einen interaktiven Wizard gebaut, der dich durch die Konfiguration führt:
   ```bash
   uv run python scripts/onboard.py
   ```
   *Folge den Anweisungen im Terminal, um deinen Telegram-Token, dein HKA-Login und deinen bevorzugten LLM-Provider einzurichten.*

## 🚀 Betrieb

Starten des Bots:
```bash
make run
```
Sobald der Bot läuft, öffnet sich das **Live Dashboard** in deinem Terminal. Du hast direkten Zugriff auf interaktive Admin-Befehle.

### 💻 Konsolen-Befehle (Terminal)
Während der Bot läuft, kannst du im Terminal Befehle eintippen:
- `status`: Zeigt das aktuelle Live-Dashboard an.
- `loglevel <level>`: Ändert das Log-Level dynamisch (`info`, `debug`, `warning`).
- `sync`: Stößt den Neuaufbau der Kurs- und Dozenten-Indizes an.
- `help`: Zeigt alle Befehle.
- `exit`: Fährt den Bot sauber herunter.

### 📱 Telegram Admin-Befehle
Wenn du deine Telegram-ID in der Konfiguration als Admin hinterlegt hast, stehen dir im Chat folgende Befehle zur Verfügung:
- `/loglevel <level>`: Ändert das Logging aus der Ferne.
- `/setprovider <provider>`: Wechselt das KI-Modell (z.B. `mistral`, `claude`, `gemini`).
- `/sync`: Synchronisiert die Dozenten- und Kursdaten neu.
- `/stats`: Zeigt Token-Verbrauch und System-Limits.

## 🧠 Architektur

Der Agent nutzt einen **Hybrid-Ansatz** zur Kosten- und Geschwindigkeitsoptimierung:
1. **User Input:** Der Nutzer sendet eine Nachricht an den Telegram-Bot.
2. **LLM Intent-Extraction:** Ein leichtgewichtiges Modell (z.B. Mistral Small) liest die Nachricht und generiert ein maschinenlesbares JSON (Tool-Calls).
3. **Execution:** Python führt die Tool-Calls (z.B. `get_room_timetable`) asynchron gegen die HKA-API aus.
4. **Formatting:** Python formatiert die API-Antworten in sauberes Markdown und sendet es an den Nutzer zurück (kein zweiter teurer LLM-Call für die Formatierung!).

## 🤝 Mitwirken
Pull Requests sind willkommen! Für größere Änderungen eröffne bitte zuerst ein Issue, um zu diskutieren, was du ändern möchtest.
