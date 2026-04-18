# Issue: Fehlender/Überschriebener Konsolen-Prompt (console-entry)

## Hintergrund & Motivation
Nutzer berichten, dass nach der Bearbeitung einer Anfrage über Telegram im lokalen Terminal kein Eingabeprompt (`raumzeit> `) mehr sichtbar ist. Das Terminal wirkt "eingefroren" oder abgestürzt, da die Hintergrund-Logs (z.B. "Tokens: input=...") den ursprünglichen Prompt überschreiben und der Cursor danach in einer leeren Zeile blinkt.

## Ursachenanalyse / Ist-Zustand
Das Terminal nutzt in `src/terminal.py` eine Endlosschleife mit `await asyncio.to_thread(input, "raumzeit> ")`. 
Da die Verarbeitung von Telegram-Nachrichten asynchron im Hintergrund läuft, schreiben die Logger (`RichHandler` in `src/bot.py`) ihre Ausgaben direkt in den `stdout`. Dabei scrollt der ursprüngliche `raumzeit> ` Prompt nach oben weg. Die Standard-`input()`-Funktion von Python weiß nichts von diesen Hintergrundausgaben und druckt den Prompt nicht neu, weshalb der Nutzer in einer leeren Zeile landet.

## Lösungsvorschlag
Da wir `rich` für das Logging nutzen, können wir das Problem elegant lösen, indem wir den `RichHandler` oder die Konsolenausgabe so anpassen, dass der Prompt nach asynchronen Log-Ausgaben wiederhergestellt wird. Da ein vollständiges Redraw des Prompts bei `input()` schwierig ist, gibt es einen Trick mit `rich.console.Console`:
Wir können den Prompt nach jeder Bot-Antwort explizit im Terminal neu zeichnen, oder wir schreiben einen kleinen Wrapper um `input`, bzw. einen dedizierten Log-Handler.

Eine viel einfachere und effektivere Methode in asynchronen CLI-Apps ohne komplexe GUI (wie Textual) ist es, nach der Verarbeitung einer Telegram-Nachricht (die die Logs erzeugt) einen kurzen Hinweis oder einen neuen Prompt zu printen. 
Noch eleganter: Wir patchen den Logger oder nutzen ein unsichtbares `print("raumzeit> ", end="", flush=True)`, wenn der Bot fertig ist.

Ein minimalinvasiver Fix für unser spezielles Problem:
Wir passen den `RichHandler` nicht an, sondern erweitern `src/bot.py`, sodass am Ende der `handle_message` Funktion, nachdem alle Logs geschrieben wurden (inkl. Token-Info), dem Terminal-Nutzer signalisiert wird, dass die Eingabe wieder aktiv ist.
Besser: Wir fangen das im `terminal.py` ab oder bauen einen Custom Handler, der nach einem Log-Event den Input-Prompt neu schreibt.

Da wir aber eine robuste Lösung wollen: Wir ersetzen das blockierende `input("raumzeit> ")` durch eine asynchrone Eingabeschleife (mittels `aioconsole` falls verfügbar, sonst `sys.stdin` lesen), oder wir schreiben einfach einen Custom Log Handler, der den Prompt neu zeichnet.
Alternativ: Wir überschreiben `sys.stdout._write` temporär? Nein, zu hacky.

**Der beste chirurgische Fix (Surgical Edit):**
Wir erstellen in `src/terminal.py` eine globale Variable `NEEDS_PROMPT = False`.
Im `RichHandler` können wir nicht ohne weiteres eingreifen. Aber wir können in `src/bot.py` nach dem erfolgreichen Ausführen des Agenten einen Befehl an das Terminal senden, den Prompt neu zu zeichnen.
Noch einfacher: Wenn der Nutzer im Terminal "Enter" drückt, bekommt er den Prompt sowieso neu. Wir können einfach am Anfang von `terminal_loop` den Prompt nur bei Bedarf printen oder `sys.stdout.write("\rraumzeit> "); sys.stdout.flush()` nutzen.
Lass uns `prompt_toolkit` nutzen, falls installiert, ansonsten einen simplen Fix:
Wir schreiben eine kleine Wrapper-Klasse für den `Console` Output in `terminal.py`, die sich merkt, wann geschrieben wurde, und den Prompt neu zeichnet.

Da wir `rich` bereits verwenden: `rich.prompt.Prompt.ask` blockiert ebenfalls.
Wir können stattdessen in `src/bot.py` am Ende der asynchronen Verarbeitung prüfen, ob wir im Interaktiven Modus sind (`not IS_DAEMON`), und wenn ja, `sys.stdout.write("\nraumzeit> "); sys.stdout.flush()` aufrufen.

### Konkrete Umsetzung:
In `src/bot.py` in der Funktion `handle_message` am Ende:
```python
    if not IS_DAEMON:
        # Den Prompt für den lokalen Konsolennutzer neu zeichnen
        import sys
        sys.stdout.write("\rraumzeit> ")
        sys.stdout.flush()
```
Das ist sicher, leichtgewichtig und erfordert keine neuen Abhängigkeiten.

## Umsetzungsschritte
1. **`src/bot.py`**:
   - Am Ende von `handle_message` (nach `await _send_reply(...)` und Token-Logging) fügen wir den Code ein, um den `raumzeit> ` Prompt neu zu schreiben, falls `not IS_DAEMON` zutrifft.
   - Da die Token-Ausgabe in `bot.py` geloggt wird (oder in `agent.py`?), müssen wir sicherstellen, dass es als letztes passiert.
2. Wir verifizieren, ob die Token-Ausgabe (die der Nutzer im Issue zeigt) das Letzte ist, was ausgegeben wird. Laut Log im Issue ist `INFO Tokens: input=1074...` das Letzte. Das passiert wahrscheinlich in `handle_message` oder im `agent.py`.

## Verifizierung & Testing
- Wir prüfen `src/bot.py` und `src/agent.py` auf die Token-Ausgabe.
- Wir fügen den Redraw des Prompts ein.
- Testen im interaktiven Modus: Nachricht simulieren und schauen, ob der Prompt danach wieder da ist.
