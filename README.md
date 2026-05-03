# 🌌 HKA Raumzeit KI-Agent

Ein hochmoderner, autonomer KI-gestützter Telegram-Bot für Studierende der Hochschule Karlsruhe (HKA). Der Bot nutzt Large Language Models (LLMs) und ein spezialisiertes Multi-Agenten-System, um natürliche Sprache zu verstehen und präzise Informationen aus der Raumzeit-API, dem Mensa-Plan und den Personenverzeichnissen der HKA zu extrahieren.

Der Bot kombiniert die Flexibilität von KI-Intents mit der Zuverlässigkeit deterministischer Tool-Ausführung – Fakten werden nie "halluziniert", sondern direkt aus den offiziellen Schnittstellen abgefragt.

---

## ✨ Hauptfunktionen

- 🏫 **Raumbelegung**: *"Wann ist Raum M-102 heute frei?"* oder *"Wo ist morgen um 10 Uhr etwas frei?"*
- 📅 **Stundenpläne**: Abfrage für Studiengänge (z.B. MABB.2) oder Dozenten.
- 🎓 **Personalisierung**: Speichere deine Kurse mit `/setcourse` und frage einfach: *"Was habe ich heute?"*
- 🍴 **Mensa-Plan**: Aktuelle Menüs der Mensa Moltke via GraphQL inkl. Allergenen und Preisen.
- 🗺️ **Campus-Karten**: Automatische Generierung von Lageplänen mit markierten Gebäuden und Stockwerks-Infos.
- ⚔️ **Konflikt-Analyse**: *"Finde Überschneidungen zwischen MABB.2 und EIBB.2."*
- 🛡️ **Admin-Suite**: Umfangreiche Tools zur Systemüberwachung, Nutzerverwaltung und Daten-Synchronisation.

---

## 🏗 Architektur

Der Bot folgt einer strikten Trennung zwischen Sprachverständnis und Datenverarbeitung:

1.  **Router**: Analysiert die Nachricht mittels Heuristiken (Fast-Path) oder LLM-Klassifizierung.
2.  **Agent**: Wandelt den erkannten Intent in strukturierte Tool-Calls (JSON) um.
3.  **Tools**: Führen den deterministischen Python-Code aus (Scraping, DB-Abfragen, API-Calls).
4.  **Formatter**: Bereitet die Rohdaten in sicherem Telegram-Markdown auf.

### 🗄️ Das 3-Säulen-Datenmodell
Alle Daten liegen standardmäßig in `data/` und sind aufgeteilt:
- `state.db`: Nutzerprofile, gespeicherte Kurse und Gesprächshistorien.
- `cache.db`: Hochperformante Caches für API-Ergebnisse und Mensa-Pläne.
- `telemetry.db`: Statistiken, Token-Verbrauch und System-Logs.

---

## 🚀 Quickstart

### Voraussetzungen
- Python **3.11+**
- [uv](https://github.com/astral-sh/uv) (empfohlen für Paketmanagement)
- Ein Telegram-Bot-Token vom [@BotFather](https://t.me/botfather)
- Ein LLM API-Key (Gemini, Anthropic, OpenAI, Groq oder Mistral)

### Installation & Start
```bash
# 1. Repository klonen
git clone https://github.com/Bayyo1337/hka-agentic-raumzeit-bot.git
cd hka-agentic-raumzeit-bot

# 2. Abhängigkeiten installieren
uv sync

# 3. Konfiguration einrichten
cp .env.example .env
# Öffne .env und trage deine Keys ein (siehe Abschnitt Konfiguration)

# 4. Initialisierung (Daten & Karten)
uv run python scripts/setup/onboard.py
uv run python scripts/setup/generate_maps.py

# 5. Bot starten
make run
```

---

## ⚙️ Konfiguration

Die Konfiguration erfolgt über die `.env` Datei.

| Variable | Erforderlich | Beschreibung | Beispiel |
| :--- | :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Ja | API-Token von Telegram | `123456:ABC...` |
| `RAUMZEIT_LOGIN` | Ja | HKA-Account Login (für API) | `abcd1011` |
| `RAUMZEIT_PASSWORD` | Ja | HKA-Account Passwort | `********` |
| `LLM_PROVIDER` | Ja | Provider: `gemini`, `anthropic`, `openai`, `groq`, `mistral` | `gemini` |
| `LLM_MODEL` | Nein | Spezifisches Modell (Standard: provider-dependent) | `gemini-1.5-flash` |
| `GEMINI_API_KEY` | Ja* | API Key für Google Gemini (falls Provider=gemini) | `AIza...` |
| `ALLOWED_USER_IDS` | Nein | Komma-getrennte IDs (Leer = alle erlaubt) | `12345,67890` |
| `ADMIN_USER_IDS` | Ja | Komma-getrennte IDs für Admin-Rechte | `12345` |
| `LOG_LEVEL` | Nein | `DEBUG`, `INFO`, `WARNING` (Standard: `INFO`) | `INFO` |

*\*Je nach gewähltem Provider muss der entsprechende Key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.) gesetzt sein.*

---

## 🛡 Datenschutz (DSGVO)
Deine Privatsphäre ist uns wichtig. Der Bot implementiert:
- **Datenminimierung**: Es wird nur gespeichert, was für die Funktion nötig ist.
- **Kontrolle**: Mit `/data`, `/export` und `/delete` behältst du die volle Kontrolle über deine Daten.
- **Transparenz**: Alle Speicherorte und Zwecke sind in der [Datenschutzerklärung](docs/DSGVO.md) dokumentiert.
- **PII-Redaktion**: "Best-Effort" Schwärzung von E-Mails, Telefonnummern und IBANs vor der KI-Verarbeitung oder Log-Speicherung.
- **Telemetrie-Opt-Out**: Vollständiger Bypass des Rate-Limitings und der Telemetrie-Speicherung bei Widerspruch.

---

## 📱 Telegram Kommandos

### Nutzer-Befehle
- `/start`: Begrüßung und erste Schritte.
- `/help`: Detaillierte Hilfe und Beispielfragen.
- `/privacy`: Datenschutz-Informationen und Link zur DSGVO-Erklärung.
- `/consent`: Verwalte deine Privacy-Einstellungen (Was darf gespeichert werden?).
- `/data`: Zeigt alle über dich gespeicherten Daten an.
- `/export`: Exportiert deine Daten als JSON-Datei.
- `/delete`: Löscht alle deine personenbezogenen Daten unwiderruflich.
- `/setcourse`: Interaktiver Assistent zum Speichern deiner Kurse (Multi-Select).
- `/myplan`: Zeigt deinen personalisierten Stundenplan für heute.
- `/mensa`: Aktueller Speiseplan der Mensa Moltke.
- `/stats`: Token-Verbrauch und Profil-Status.
- `/bug`: Fehler oder Feedback an die Entwickler melden.
- `/reset`: Löscht deinen aktuellen Gesprächskontext mit der KI.

### Admin-Befehle (nur für `ADMIN_USER_IDS`)
- `/admin`: Zentrales Dashboard für Systemstatus & Statistiken.
- `/sync [all|courses|lecturers]`: Manuelle Daten-Synchronisation mit der HKA.
- `/maintenance`: Schaltet den KI-Wartungsmodus ein/aus.
- `/broadcast [text]`: Sendet eine Nachricht an alle registrierten Nutzer.
- `/user [id/name]`: Sucht Informationen zu einem bestimmten Nutzer.
- `/ban`/`/unban [id]`: Sperrt oder entsperrt Nutzer.
- `/loglevel [level]`: Ändert die Detailtiefe der Logs im laufenden Betrieb.
- `/togglepersonal`: Aktiviert/Deaktiviert globale Personalisierungs-Features.
- `/togglemap`: Aktiviert/Deaktiviert die Karten-Generierung.
- `/rooms`: Statusbericht über die Raumbelegung und Datenbank-Konsistenz.
- `/ping`: Einfacher Verbindungs- und Latenzcheck.
- `/indexage` & `/courses`: Status des Kurs-Index und Liste der Studiengänge.
- `/clearhistory`: Löscht die Historie eines Nutzers (Admin-Sicht).

---

## 🛠 Entwicklung & Qualitätssicherung

### Make-Targets
- `make run`: Startet den Bot inkl. Dashboard.
- `make check`: Führt einen System-Check der Umgebung durch.
- `make test-e2e-dynamic`: Erzeugt dynamische Testfälle und führt End-to-End Tests aus.
- `make lint`: Prüft den Code-Stil mittels `ruff`.
- `make clean`: Bereinigt Cache und temporäre Dateien.

### Projekt-Konventionen
- **Issues & Features**: Neue Aufgaben werden in `.gemini/prompts/` analysiert und in `features/specs/` spezifiziert.
- **Logs**: Reale Session-Logs werden unter `.gemini/logs/` archiviert und in `session_log.md` indiziert.
- **Tests**: Neue Features müssen durch Tests in `tests/` (z.B. `test_personalization.py`) abgesichert werden.

---

## ❓ Fehlerbehebung (FAQ)

**Q: Der Bot antwortet "Keine Belegungen gefunden", obwohl Vorlesungen stattfinden.**
A: Prüfe mit `/indexage`, wie alt der Index ist. Nutze `/sync courses`, um die Daten zu aktualisieren. Manchmal liefert die HKA-API für sehr spezifische Filter keine Ergebnisse.

**Q: Die Karte zeigt das falsche Gebäude.**
A: Die Karten-Logik basiert auf Regex-Matching der Raumnamen (z.B. "M-102" -> Gebäude M). Falls ein Raum nicht erkannt wird, melde dies bitte per `/bug`.

**Q: Telegram zeigt "Error: Can't find end of the entity".**
A: Dies deutet auf einen Formatierungsfehler hin. Der Bot nutzt einen globalen Escaper, aber bei neuen Tools muss auf `src/formatter.py` geachtet werden.

---

## 📜 Lizenz & Disclaimer

Dieses Projekt ist unter der **AGPL-3.0** lizenziert.

**Disclaimer**: Dies ist ein **inoffizielles** Projekt von Studierenden für Studierende. Es besteht keine offizielle Verbindung zur Hochschule Karlsruhe (HKA). Die Daten stammen aus öffentlich zugänglichen oder studentisch genutzten Schnittstellen und sind ohne Gewähr.
