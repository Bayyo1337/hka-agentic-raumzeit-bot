# Vorbereitung für 24/7 Betrieb im Linux LXC (Prozessmanagement)

Dieses Dokument beschreibt die Maßnahmen, um den Raumzeit KI-Agent stabil und wartungsarm als Dauerprozess (Daemon) in einem Linux-Container (LXC) oder auf einem Server zu betreiben.

## 1. Systemd-Service einrichten (Empfohlen)
Um den Bot als Hintergrundprozess laufen zu lassen, empfiehlt sich die Nutzung von `systemd`. Dadurch startet der Bot nach einem Server-Neustart automatisch und wird bei Abstürzen neu gestartet.

**Vorgehen:**
Eine Datei unter `/etc/systemd/system/raumzeit.service` anlegen:

```ini
[Unit]
Description=Raumzeit KI-Agent (Telegram Bot)
After=network.target

[Service]
Type=simple
User=dein_benutzer
WorkingDirectory=/pfad/zum/bot/hka-agentic-raumzeit-bot
# uv in den PATH aufnehmen oder absoluten Pfad nutzen
ExecStart=/usr/local/bin/uv run python -m src.bot
Restart=always
RestartSec=10
# Deaktiviert gepuffertes Logging (Logs tauchen sofort auf)
Environment=PYTHONUNBUFFERED=1
# Teilt dem Bot mit, dass er als Daemon läuft (optional, wird meist autodetektiert)
Environment=RUN_AS_DAEMON=1

[Install]
WantedBy=multi-user.target
```

**Befehle:**
*   `sudo systemctl daemon-reload`
*   `sudo systemctl enable raumzeit.service`
*   `sudo systemctl start raumzeit.service`
*   `sudo journalctl -u raumzeit.service -f` (Logs anzeigen)

## 2. Automatischer Background-Sync ✅
**Status: Implementiert.**
Der Bot verfügt über einen internen Scheduler, der jede Nacht um **04:00 Uhr** automatisch einen vollständigen Abgleich der Kurs- und Dozentenindizes durchführt. Ein manueller Cronjob hierfür ist nicht mehr erforderlich.

## 3. Log-Formatierung (Daemon-Modus) ✅
**Status: Implementiert.**
Der Bot erkennt automatisch, ob er in einem Terminal (`isatty`) oder als Hintergrunddienst läuft. Im Daemon-Modus wird das interaktive Rich-Dashboard deaktiviert und auf ein flaches, Systemd-kompatibles Log-Format umgeschaltet.

## 4. Datenbank-Backups (SQLite)
Alle Nutzerdaten liegen in `data/bot.db`. Es wird empfohlen, einen Cronjob auf dem Host-System für tägliche Backups einzurichten:

```bash
0 3 * * * sqlite3 /pfad/zum/bot/data/bot.db ".backup '/pfad/zum/bot/data/backup_$(date +\%F).db'"
```

## 5. Auto-Reconnect / Watchdog ✅
**Status: Implementiert.**
Ein interner Watchdog im `_error_handler` zählt aufeinanderfolgende Netzwerkfehler. Bei dauerhaften Verbindungsproblemen (z.B. 15 Fehler in Folge) beendet sich der Prozess selbst mit `sys.exit(1)`, um durch `systemd` einen sauberen Neustart zu erzwingen.

---
*Stand: April 2026 – Der Bot ist vollständig für den 24/7 Betrieb optimiert.*
