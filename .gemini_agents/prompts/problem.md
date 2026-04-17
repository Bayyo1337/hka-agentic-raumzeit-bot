# Bugfix: Telegram Message Too Long

## Hintergrund & Motivation
Bei umfangreichen Stundenplan-Abfragen oder Konflikt-Analysen kann die Antwort des Bots das Telegram-Limit von 4096 Zeichen überschreiten. In diesem Fall verweigert die API den Versand mit `BadRequest: Message is too long`.

## Ursachenanalyse / Ist-Zustand
Der Traceback zeigt, dass `update.message.reply_text` fehlschlägt. Die aktuelle Fehlerbehandlung in `_send_reply` versucht zwar, die Nachricht ohne Markdown zu senden, falls der erste Versuch scheitert, aber das hilft nicht gegen das Längenlimit.

Repro-Ergebnis:
`CAUGHT: Message too long`
`Test failed as expected`

## Lösungsvorschlag
Die Nachricht muss in kleinere Stücke (Chunks) zerlegt werden, die jeweils das Limit nicht überschreiten.
1. Implementierung einer `split_message`-Hilfsfunktion, die bevorzugt an Zeilenumbrüchen trennt.
2. Anpassung von `_send_reply` in `src/bot.py`, um die Nachricht in Chunks zu senden, falls sie zu lang ist.

## Umsetzungsschritte
1. **Hilfsfunktion `_chunk_message(text, limit=4000)`** in `src/bot.py` oder einem Utility-Modul hinzufügen.
2. **`_send_reply` anpassen**:
   - Prüfe die Länge von `reply`.
   - Falls > 4000, teile die Nachricht.
   - Sende jeden Teil einzeln.
   - Stelle sicher, dass `_bot_messages` alle Teil-Nachrichten erfasst, damit `/clear` weiterhin funktioniert.

## Verifizierung & Testing
- Ausführen des Repro-Skripts `scripts/repro_issue.py` (angepasst auf Chunks).
- Manueller Test mit einer sehr langen Nachricht (z.B. Brute-Force Abfrage für einen vollen Studiengang).
