# Vorbereitung für 24/7 Betrieb im Linux LXC (Prozessmanagement)

Dieses Dokument fasst die wichtigsten Maßnahmen zusammen, um den Raumzeit KI-Agent stabil und wartungsarm als Dauerprozess (Daemon) in einem Linux-Container (LXC) oder auf einem Server zu betreiben.

## 1. Systemd-Service einrichten
Um den Bot als Hintergrundprozess laufen zu lassen (ohne blockiertes Terminalfenster), empfiehlt sich die Nutzung von `systemd`. Dadurch startet der Bot nach einem Server-Neustart automatisch und wird bei Abstürzen (z.B. nach Netzwerkabbrüchen) neu gestartet.

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
# Teilt dem Bot mit, dass er als Daemon läuft
Environment=RUN_AS_DAEMON=1

[Install]
WantedBy=multi-user.target
```

**Befehle:**
*   `sudo systemctl daemon-reload`
*   `sudo systemctl enable raumzeit.service`
*   `sudo systemctl start raumzeit.service`
*   `sudo journalctl -u raumzeit.service -f` (Logs anzeigen)

## 2. Automatischer Background-Sync
Aktuell werden die Indizes für Kurse und Dozenten manuell (via `/sync` oder in der Konsole) aufgebaut. Im Dauerbetrieb sollte dies automatisiert geschehen.

**To-Do:**
*   Implementierung eines asynchronen Schedulers (z.B. `APScheduler` oder eine einfache `asyncio.sleep`-Schleife in `src/bot.py`).
*   Tägliche Ausführung (z.B. nachts um 04:00 Uhr) von `build_lecturer_index()` und `save_course_index()`.

## 3. Log-Formatierung (Daemon-Modus)
Das aktuelle interaktive Dashboard (`rich.live.Live`) und die farbigen Logs (`RichHandler`) sind für die manuelle Terminal-Bedienung optimiert. Läuft der Bot als Systemd-Service, fluten die Escape-Sequenzen das `journalctl`.

**To-Do:**
*   Eine Abfrage in `src/bot.py` einbauen: `if not sys.stdout.isatty() or os.environ.get("RUN_AS_DAEMON"):`
*   Wenn der Bot im Daemon-Modus läuft:
    *   Verwendung des regulären `logging.StreamHandler` statt `RichHandler`.
    *   Deaktivierung des Live-Dashboards und der `terminal_loop`.

## 4. Datenbank-Backups (SQLite)
Alle Nutzerdaten (Statistiken, Limits, Sperren, History) liegen in `data/bot.db`.

**To-Do:**
*   Einrichtung eines Cronjobs auf dem Host-System für tägliche Backups:
    ```bash
    0 3 * * * sqlite3 /pfad/zum/bot/data/bot.db ".backup '/pfad/zum/bot/data/backup_$(date +\%F).db'"
    ```
*   Optional: Alte Backups automatisch löschen (z.B. nach 7 Tagen).

## 5. Auto-Reconnect / Watchdog
Bei längeren Netzwerkausfällen (z.B. Wartungsarbeiten am Hochschulnetz oder Problemen bei den Telegram-Servern) kann sich die Polling-Schleife aufhängen.

**To-Do:**
*   Den `_error_handler` in `src/bot.py` erweitern: Wenn gehäuft `NetworkError`s auftreten, sollte der Bot den Prozess mit `sys.exit(1)` beenden.
*   Dadurch greift das `Restart=always` aus der Systemd-Unit (Punkt 1) und der Bot startet mit einer sauberen Verbindung neu.
