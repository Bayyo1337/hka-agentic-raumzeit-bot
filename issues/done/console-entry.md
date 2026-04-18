wenn über telegram ein befehl reinkommt, wird der schön in der konsole geprinted, allerdings steht danach dann einfach ein leeres feld:            DEBUG    LLM → tool: get_lecturer_info({'account': 'Offermann'})                                                        
           INFO     Dozenten-Index geladen: 1216 Einträge                                                                          
           DEBUG    Bot Antwort: 👤 *Dozenten-Info: Prof. Dr.-Ing. Peter Offermann*                                                
                    📧 E-Mail: peter.offermann@h-ka.de                                                                             
                    🕒 Sprechzeit: nach Vereinbarung                                                                               
           INFO     Tokens: input=1074 output=27 gesamt=1101                                                                       
(diese Zeile hier ist aktiv)

ich habe dir sie mit (diese Zeile hier ist aktiv) markiert, dort kann man dann neue befehle eingeben, auf den ersten blick sieht es aber aus, wie wenn er gevrasht ist. Kannst du das ändern?

---
## Lösung
Das Problem entstand dadurch, dass die Hintergrund-Prozesse der Telegram-Behandlung Logs in das Terminal geschrieben haben, während die Eingabeaufforderung (`input()`) des Haupt-Threads darauf wartete, dass der Nutzer etwas eingibt. Dadurch "scrollte" der Prompt nach oben weg.

In `src/bot.py` wurde ein Fix eingebaut: Am Ende der asynchronen Verarbeitung von Nachrichten (`handle_message`), nachdem alle relevanten Logs ausgegeben wurden, prüft der Bot nun, ob er im lokalen/interaktiven Modus läuft (`not IS_DAEMON`). Ist dies der Fall, wird der Prompt `raumzeit> ` gezielt über den Terminal-Buffer (`sys.stdout.write`) neu gezeichnet. So sieht der Nutzer sofort, dass das System bereit für neue Befehle ist.
