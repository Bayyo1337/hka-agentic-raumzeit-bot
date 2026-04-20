# Problem: Irreführender Mensa-Hinweistext und fehlender Shortcut

## Hintergrund & Motivation
Nutzer erhalten bei fehlgeschlagenen Allergen-Abfragen den Hinweis: "Bitte rufe erst das Mensa-Menü mit /mensa ab." Allerdings existiert der Command `/mensa` aktuell nicht, da die Funktion primär über natürliche Sprache gesteuert wird. Dies führt zu Verwirrung, wie im Issue `mensa-abfrage.md` dokumentiert.

## Ursachenanalyse / Ist-Zustand
1. **Inkorrekter Text:** In `src/tools.py` ist der Error-String hart codiert und verweist auf einen nicht existierenden Command.
2. **Fehlende Erwartungserfüllung:** Nutzer erwarten intuitiv einen `/mensa` Command, um den Speiseplan schnell abzurufen, ohne einen vollständigen Satz schreiben zu müssen.

## Lösungsvorschlag
1. **Textkorrektur:** Änderung des Hinweistextes in `src/tools.py` auf eine neutrale Formulierung: "Bitte frage erst nach dem Mensa-Plan."
2. **Shortcut-Implementierung:** Hinzufügen eines echten `/mensa` Command-Handlers in `src/bot.py`. Dieser soll standardmäßig die Mensa Moltke für den aktuellen Tag abrufen.

## Umsetzungsschritte

### 1. `src/tools.py`
- In der Funktion `get_mensa_meal_details` den Rückgabewert für den Fehlerfall anpassen:
  `"Gerichts-Details aktuell nicht verfügbar. Bitte frage erst nach dem Mensa-Menü."`

### 2. `src/admin.py` (oder neues Command in bot.py)
- Da `/mensa` ein Nutzer-Command ist, sollte er in `src/bot.py` oder einem passenden Modul definiert werden. Wir fügen ihn in `src/bot.py` hinzu.
- Funktion `cmd_mensa(update, context)` implementieren:
  - Ruft `raumzeit.get_mensa_menu()` auf.
  - Formatiert das Ergebnis mit `formatter.format_results`.
  - Sendet die Antwort.

### 3. `src/bot.py`
- Den neuen Handler registrieren: `app.add_handler(CommandHandler("mensa", cmd_mensa))`.
- Den Command in die Liste `_USER_COMMANDS` aufnehmen, damit er im Telegram-Menü erscheint.

## Verifizierung & Testing
1. Ausführen des Repro-Skripts `scripts/repro_mensa_command.py` (angepasst auf den neuen Text).
2. Manueller Test des neuen `/mensa` Commands im Bot.
