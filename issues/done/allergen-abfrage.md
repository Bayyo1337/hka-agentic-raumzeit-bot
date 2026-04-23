Was sind in Wahlessen 2 für allergene enthalten?
🍱 Pommes

Keine Allergene oder Zusatzstoffe gelistet.
Was sind in 3 Semmelknödel mit frischen Champignonragout für allergene enthalten?
🍱 3 Semmelknödel mit frischen Champignonragout

Allergene:
Ei, Milch, Sesam, Weizen

Zusatzstoffe:
Farbstoff

Wenn ich nach Wahlessen 2 frage, sollte es alle Allergene des Menüs ausgeben 


raumzeit> [13:46:13] DEBUG    Anfrage von @Noah_Richter (chat=533286058): Was sind in Wahlessen 2 für allergene enthalten?                                                                                        
           DEBUG    User @Noah_Richter (Intent: smalltalk_fallback): Was sind in Wahlessen 2 für allergene enthalten?                                                                                   
           DEBUG    LLM Extraktion: {"calls": [{"tool": "get_mensa_meal_details", "args": {"meal_id": "wahlessen2"}}]}                                                                                  
           INFO     Mensa-Detail: Pattern-Match für 'wahlessen2' -> 'Pommes' (ID: 9d61c94b-0110-4006-8ad3-2a0eba95af5a)

Und die Debug AUsgabe ist nicht vollständig, es fehlen die Angaben zum llm, tokens, welcher prompt usw

Warum wurde eigentlich als intent der smalltalk_fallback genommen? Wann werden die anderen Prompts genommen?

