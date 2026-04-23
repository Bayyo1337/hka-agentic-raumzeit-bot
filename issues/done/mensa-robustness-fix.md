/mensa
🍴 Mensa Moltke
📅 Mo, 20.04.2026

Aktionstheke
  🥩 Reine Kalbsbratwurst mit Currysauce (2.60€)
  🌱 Vegane Bratwurst auf Basis von Erbsen und Weizenprotein mit Currysoße (2.40€)
  🌱 koerifrites (1.50€)

Buffet
  🥕 Salatbuffet überwiegend vegetarisch je 100g (1.10€)

Gut & Günstig
  🥩 Alaska -Seelachs -Gemüseragout mit Reis (3.60€)
  🌱 Soja-Ragout mit Reis (3.60€)

Wahlessen 1
  🌱 Linsen-Kokos-Pfanne mit Currykartoffeln (3.55€)
  🥩 Schnitzel Bar Puten und Schweineschnitzel je 100 g in Selbstbedienung (1.10€)
  🌱 Pommes (1.10€)

Wahlessen 2
  🥩 Hähnchen Cordon bleu mit Putenschinken Bratensoße Pommes (5.05€)
  🥕 Dessertauswahl Diverse Desserts ab 0,50 EUR bis (1.05€)
  🥕 Grießpudding (0.95€)
  🥕 Salat (0.90€)

Frage nach Details zu einem Gericht für Allergene.
Details zu Wahlessen 1
❌ Gerichts-Details aktuell nicht verfügbar. Bitte frage erst nach dem Mensa-Menü.
Details zu Alaska -Seelachs -Gemüseragout mit Reis
🍴 Mensa Moltke
📅 Mo, 20.04.2026

Aktionstheke
  🥩 Reine Kalbsbratwurst mit Currysauce (2.60€)
  🌱 Vegane Bratwurst auf Basis von Erbsen und Weizenprotein mit Currysoße (2.40€)
  🌱 koerifrites (1.50€)

Buffet
  🥕 Salatbuffet überwiegend vegetarisch je 100g (1.10€)

Gut & Günstig
  🥩 Alaska -Seelachs -Gemüseragout mit Reis (3.60€)
  🌱 Soja-Ragout mit Reis (3.60€)

Wahlessen 1
  🌱 Linsen-Kokos-Pfanne mit Currykartoffeln (3.55€)
  🥩 Schnitzel Bar Puten und Schweineschnitzel je 100 g in Selbstbedienung (1.10€)
  🌱 Pommes (1.10€)

Wahlessen 2
  🥩 Hähnchen Cordon bleu mit Putenschinken Bratensoße Pommes (5.05€)
  🥕 Dessertauswahl Diverse Desserts ab 0,50 EUR bis (1.05€)
  🥕 Grießpudding (0.95€)
  🥕 Salat (0.90€)

Frage nach Details zu einem Gericht für Allergene.
/mensa
🍴 Mensa Moltke
📅 Mo, 20.04.2026

Aktionstheke
  🥩 Reine Kalbsbratwurst mit Currysauce (2.60€)
  🌱 Vegane Bratwurst auf Basis von Erbsen und Weizenprotein mit Currysoße (2.40€)
  🌱 koerifrites (1.50€)

Buffet
  🥕 Salatbuffet überwiegend vegetarisch je 100g (1.10€)

Gut & Günstig
  🥩 Alaska -Seelachs -Gemüseragout mit Reis (3.60€)
  🌱 Soja-Ragout mit Reis (3.60€)

Wahlessen 1
  🌱 Linsen-Kokos-Pfanne mit Currykartoffeln (3.55€)
  🥩 Schnitzel Bar Puten und Schweineschnitzel je 100 g in Selbstbedienung (1.10€)
  🌱 Pommes (1.10€)

Wahlessen 2
  🥩 Hähnchen Cordon bleu mit Putenschinken Bratensoße Pommes (5.05€)
  🥕 Dessertauswahl Diverse Desserts ab 0,50 EUR bis (1.05€)
  🥕 Grießpudding (0.95€)
  🥕 Salat (0.90€)

Frage nach Details zu einem Gericht für Allergene.


raumzeit> [16:39:07] DEBUG    Anfrage von @Noah_Richter (chat=533286058): Details zu Wahlessen 1                                                                                                                    
           DEBUG    User @Noah_Richter: Details zu Wahlessen 1                                                                                                                                            
           DEBUG    Vollständiger Prompt für LLM:                                                                                                                                                         
                    [                                                                                                                                                                                     
                      {                                                                                                                                                                                   
                        "role": "system",                                                                                                                                                                 
                        "content": "Du bist ein Intent-Parser für das Raumzeit-Buchungssystem der HKA (Hochschule Karlsruhe).\n\nAnalysiere die Nutzernachricht und gib ausschließlich valides JSON       
                    zurück. Kein Text, keine Erklärung.\n\nVerfügbare Tools:\n- get_room_timetable: room_name (z.B. \"M-102\"), date (YYYY-MM-DD, optional)\n- get_course_timetable: course_key           
                    (\"KÜRZEL.SEMESTER\", z.B. \"MABB.6\"), date (YYYY-MM-DD, optional)\n- get_lecturer_timetable: account (vollständiger Name z.B. \"Masha Taheran\", Nachname z.B. \"Taheran\", oder    
                    Kürzel z.B. \"tama0001\"), date (YYYY-MM-DD, optional)\n- get_lecturer_info: account (Name oder Kürzel) - NUTZE DIES NUR FÜR KONTAKTINFOS (E-Mail, Sprechzeit).\n- get_mensa_menu:    
                    canteen (Name z.B. \"Moltke\", \"Adenauerring\", optional), date (YYYY-MM-DD, optional). Default Canteen ist \"Moltke\".\n- get_mensa_meal_details: meal_id (technische ID aus        
                    get_mensa_menu)\n- get_all_rooms: keine Parameter\n- get_departments: keine Parameter\n- get_courses_of_study: faculty_id (optional)\n- get_university_calendar: keine Parameter\n-   
                    find_timetable_conflicts: course (z.B. \"Maschinenbau\"), base_sem (int, Semester in dem das Fach liegt), target_sem (int, Semester mit dem verglichen werden soll), module_filter    
                    (optional, z.B. \"etechnik\")\n- get_campus_map: room_or_building (z.B. \"LI-145\" oder \"Gebäude M\") - NUTZE DIES NUR BEI FRAGEN NACH DEM ORT/STOCKWERK!\n\nRegeln:\n- Konkreter Tag
                    genannt (\"Montag\", \"nächste Woche Dienstag\", \"heute\", \"morgen\"): GENAU 1 Call mit diesem date\n- Ganze Woche (\"diese Woche\", \"nächste Woche\" ohne Tagangabe): 5 Calls für 
                    Mo–Fr mit je einem date\n- Kein Datum (\"zeig Stundenplan\"): date weglassen\n- Max. 6 Calls gesamt\n\nRegeln zur Zeitrechnung:\n- \"nächste Woche\" ohne Tag → alle 5 Tage (Mo–Fr)   
                    der nächsten Kalenderwoche.\n- \"die nächsten Tage\" / \"diese Woche\" → alle verbleibenden Tage der aktuellen Woche (inkl. Wochenende).\n- \"und sonst?\" / \"was noch?\" → restliche
                    Termine der aktuellen Woche.\n- Datum am Wochenende (Sa/So) → Normaler Call mit diesem date (API liefert auch Blockveranstaltungen).\n- Datum in der Vergangenheit → meist Tippfehler,
                    prüfe ob der gleiche Tag im nächsten Monat/Jahr gemeint sein könnte.\n\nFehler-Handling:\n- Wenn der Nutzer nach SEINEM persönlichen Plan fragt (\"mein Plan\", \"was habe ich        
                    morgen\"), aber im 'Nutzer-Profil' unten steht 'Kein Kurs hinterlegt', darfst du keinen Kurs raten! Gib in diesem Fall exakt {\"error\": \"no_course\"} zurück.\n\nKürzel-Beispiele:  
                    MABB=Maschinenbau, INFB=Informatik, IWIB=Wirtschaftsinformatik, EIMB=Elektro/IT\n\nAusgabeformat:\n{\"calls\": [{\"tool\": \"TOOLNAME\", \"args\": {\"param\": \"wert\"}},            
                    ...]}\n\nHeutiges Datum: 2026-04-20\nNutzer-Profil: Kein Kurs hinterlegt."                                                                                                            
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "was gibt es heute in der mensa?"                                                                                                                                      
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "🍴 *Mensa Moltke*\n📅 Mo, 20.04.2026\n\n*Aktionstheke*\n  🥩 Reine Kalbsbratwurst mit Currysauce (2.60€)\n  🌱 Vegane Bratwurst auf Basis von Erbsen und Weizenprotein
                    mit Currysoße (2.40€)\n  🌱 koerifrites (1.50€)\n\n*Buffet*\n  🥕 Salatbuffet überwiegend vegetarisch je 100g (1.10€)\n\n*Gut & Günstig*\n  🥩 Alaska-Seelachs-Gemüseragout mit Reis  
                    (3.60€)\n  🌱 Soja-Ragout mit Reis (3.60€)\n\n*Wahlessen 1*\n  🌱 Linsen-Kokos-Pfanne mit Currykartoffeln (3.55€)\n  🥩 Schnitzel Bar Puten und Schweineschnitzel je 100 g in         
                    Selbstbedienung (1.10€)\n  🌱 Pommes (1.10€)\n\n*Wahlessen 2*\n  🥩 Hähnchen Cordon bleu mit Putenschinken Bratensoße Eierknöpfle (5.05€)\n  🥕 Dessertauswahl Diverse Desserts ab    
                    0,50 EUR bis (1.05€)\n  🥕 Grießpudding (0.95€)\n  🥕 Salat (0.90€)\n\n_Frage nach Details zu einem Gericht für Allergene._"                                                          
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "details zu Alaska-Seelachs-Gemüseragout mit Reis"                                                                                                                     
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "❌ Gerichts-Details aktuell nicht verfügbar. Bitte rufe erst das Mensa-Menü mit /mensa ab."                                                                           
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "details zu Alaska-Seelachs-Gemüseragout mit Reis"                                                                                                                     
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "🍴 *Mensa Moltke*\n📅 Mo, 20.04.2026\n\n*Aktionstheke*\n  🥩 Reine Kalbsbratwurst mit Currysauce (2.60€)\n  🌱 Vegane Bratwurst auf Basis von Erbsen und Weizenprotein
                    mit Currysoße (2.40€)\n  🌱 koerifrites (1.50€)\n\n*Buffet*\n  🥕 Salatbuffet überwiegend vegetarisch je 100g (1.10€)\n\n*Gut & Günstig*\n  🥩 Alaska-Seelachs-Gemüseragout mit Reis  
                    (3.60€)\n  🌱 Soja-Ragout mit Reis (3.60€)\n\n*Wahlessen 1*\n  🌱 Linsen-Kokos-Pfanne mit Currykartoffeln (3.55€)\n  🥩 Schnitzel Bar Puten und Schweineschnitzel je 100 g in         
                    Selbstbedienung (1.10€)\n  🌱 Pommes (1.10€)\n\n*Wahlessen 2*\n  🥩 Hähnchen Cordon bleu mit Putenschinken Bratensoße Eierknöpfle (5.05€)\n  🥕 Dessertauswahl Diverse Desserts ab    
                    0,50 EUR bis (1.05€)\n  🥕 Grießpudding (0.95€)\n  🥕 Salat (0.90€)\n\n_Frage nach Details zu einem Gericht für Allergene._"                                                          
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "Details zu Wahlessen 1"                                                                                                                                               
                      }                                                                                                                                                                                   
                    ]                                                                                                                                                                                     
[16:39:08] DEBUG    LLM Extraktion: {"calls": [{"tool": "get_mensa_menu", "args": {"date": "2026-04-20"}}, {"tool": "get_mensa_meal_details", "args": {"meal_id": "wahlessen1"}}]}                        
           DEBUG    LLM → tool: get_mensa_menu({'date': '2026-04-20'})                                                                                                                                    
           DEBUG    LLM → tool: get_mensa_meal_details({'meal_id': 'wahlessen1'})                                                                                                                         
           WARNING  Tool 'get_mensa_meal_details' meldet Fehler: Gerichts-Details aktuell nicht verfügbar. Bitte frage erst nach dem Mensa-Menü.                                                          
           DEBUG    Bot Antwort: ❌ Gerichts-Details aktuell nicht verfügbar. Bitte frage erst nach dem Mensa-Menü.                                                                                       
           INFO     Tokens: input=1663 output=60 gesamt=1723                                                                                                                                              
raumzeit> [16:39:39] DEBUG    Anfrage von @Noah_Richter (chat=533286058): Details zu Alaska -Seelachs -Gemüseragout mit Reis                                                                                        
           DEBUG    User @Noah_Richter: Details zu Alaska -Seelachs -Gemüseragout mit Reis                                                                                                                
           DEBUG    Vollständiger Prompt für LLM:                                                                                                                                                         
                    [                                                                                                                                                                                     
                      {                                                                                                                                                                                   
                        "role": "system",                                                                                                                                                                 
                        "content": "Du bist ein Intent-Parser für das Raumzeit-Buchungssystem der HKA (Hochschule Karlsruhe).\n\nAnalysiere die Nutzernachricht und gib ausschließlich valides JSON       
                    zurück. Kein Text, keine Erklärung.\n\nVerfügbare Tools:\n- get_room_timetable: room_name (z.B. \"M-102\"), date (YYYY-MM-DD, optional)\n- get_course_timetable: course_key           
                    (\"KÜRZEL.SEMESTER\", z.B. \"MABB.6\"), date (YYYY-MM-DD, optional)\n- get_lecturer_timetable: account (vollständiger Name z.B. \"Masha Taheran\", Nachname z.B. \"Taheran\", oder    
                    Kürzel z.B. \"tama0001\"), date (YYYY-MM-DD, optional)\n- get_lecturer_info: account (Name oder Kürzel) - NUTZE DIES NUR FÜR KONTAKTINFOS (E-Mail, Sprechzeit).\n- get_mensa_menu:    
                    canteen (Name z.B. \"Moltke\", \"Adenauerring\", optional), date (YYYY-MM-DD, optional). Default Canteen ist \"Moltke\".\n- get_mensa_meal_details: meal_id (technische ID aus        
                    get_mensa_menu)\n- get_all_rooms: keine Parameter\n- get_departments: keine Parameter\n- get_courses_of_study: faculty_id (optional)\n- get_university_calendar: keine Parameter\n-   
                    find_timetable_conflicts: course (z.B. \"Maschinenbau\"), base_sem (int, Semester in dem das Fach liegt), target_sem (int, Semester mit dem verglichen werden soll), module_filter    
                    (optional, z.B. \"etechnik\")\n- get_campus_map: room_or_building (z.B. \"LI-145\" oder \"Gebäude M\") - NUTZE DIES NUR BEI FRAGEN NACH DEM ORT/STOCKWERK!\n\nRegeln:\n- Konkreter Tag
                    genannt (\"Montag\", \"nächste Woche Dienstag\", \"heute\", \"morgen\"): GENAU 1 Call mit diesem date\n- Ganze Woche (\"diese Woche\", \"nächste Woche\" ohne Tagangabe): 5 Calls für 
                    Mo–Fr mit je einem date\n- Kein Datum (\"zeig Stundenplan\"): date weglassen\n- Max. 6 Calls gesamt\n\nRegeln zur Zeitrechnung:\n- \"nächste Woche\" ohne Tag → alle 5 Tage (Mo–Fr)   
                    der nächsten Kalenderwoche.\n- \"die nächsten Tage\" / \"diese Woche\" → alle verbleibenden Tage der aktuellen Woche (inkl. Wochenende).\n- \"und sonst?\" / \"was noch?\" → restliche
                    Termine der aktuellen Woche.\n- Datum am Wochenende (Sa/So) → Normaler Call mit diesem date (API liefert auch Blockveranstaltungen).\n- Datum in der Vergangenheit → meist Tippfehler,
                    prüfe ob der gleiche Tag im nächsten Monat/Jahr gemeint sein könnte.\n\nFehler-Handling:\n- Wenn der Nutzer nach SEINEM persönlichen Plan fragt (\"mein Plan\", \"was habe ich        
                    morgen\"), aber im 'Nutzer-Profil' unten steht 'Kein Kurs hinterlegt', darfst du keinen Kurs raten! Gib in diesem Fall exakt {\"error\": \"no_course\"} zurück.\n\nKürzel-Beispiele:  
                    MABB=Maschinenbau, INFB=Informatik, IWIB=Wirtschaftsinformatik, EIMB=Elektro/IT\n\nAusgabeformat:\n{\"calls\": [{\"tool\": \"TOOLNAME\", \"args\": {\"param\": \"wert\"}},            
                    ...]}\n\nHeutiges Datum: 2026-04-20\nNutzer-Profil: Kein Kurs hinterlegt."                                                                                                            
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "details zu Alaska-Seelachs-Gemüseragout mit Reis"                                                                                                                     
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "❌ Gerichts-Details aktuell nicht verfügbar. Bitte rufe erst das Mensa-Menü mit /mensa ab."                                                                           
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "details zu Alaska-Seelachs-Gemüseragout mit Reis"                                                                                                                     
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "🍴 *Mensa Moltke*\n📅 Mo, 20.04.2026\n\n*Aktionstheke*\n  🥩 Reine Kalbsbratwurst mit Currysauce (2.60€)\n  🌱 Vegane Bratwurst auf Basis von Erbsen und Weizenprotein
                    mit Currysoße (2.40€)\n  🌱 koerifrites (1.50€)\n\n*Buffet*\n  🥕 Salatbuffet überwiegend vegetarisch je 100g (1.10€)\n\n*Gut & Günstig*\n  🥩 Alaska-Seelachs-Gemüseragout mit Reis  
                    (3.60€)\n  🌱 Soja-Ragout mit Reis (3.60€)\n\n*Wahlessen 1*\n  🌱 Linsen-Kokos-Pfanne mit Currykartoffeln (3.55€)\n  🥩 Schnitzel Bar Puten und Schweineschnitzel je 100 g in         
                    Selbstbedienung (1.10€)\n  🌱 Pommes (1.10€)\n\n*Wahlessen 2*\n  🥩 Hähnchen Cordon bleu mit Putenschinken Bratensoße Eierknöpfle (5.05€)\n  🥕 Dessertauswahl Diverse Desserts ab    
                    0,50 EUR bis (1.05€)\n  🥕 Grießpudding (0.95€)\n  🥕 Salat (0.90€)\n\n_Frage nach Details zu einem Gericht für Allergene._"                                                          
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "Details zu Wahlessen 1"                                                                                                                                               
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "❌ Gerichts-Details aktuell nicht verfügbar. Bitte frage erst nach dem Mensa-Menü."                                                                                   
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "Details zu Alaska -Seelachs -Gemüseragout mit Reis"                                                                                                                   
                      }                                                                                                                                                                                   
                    ]                                                                                                                                                                                     
           DEBUG    LLM Extraktion: {"calls": [{"tool": "get_mensa_menu", "args": {"date": "2026-04-20"}}]}                                                                                               
           DEBUG    LLM → tool: get_mensa_menu({'date': '2026-04-20'})                                                                                                                                    
           DEBUG    Bot Antwort: 🍴 *Mensa Moltke*                                                                                                                                                        
                    📅 Mo, 20.04.2026                                                                                                                                                                     
                                                                                                                                                                                                          
                    *Aktionstheke*                                                                                                                                                                        
                      🥩 Reine Kalbsbratwurst mit Currysauce (2.60€)                                                                                                                                      
                      🌱 Vegane Bratwurst auf Basis von Erbsen und Weizenprotein mit Currysoße (2.40€)                                                                                                    
                      🌱 koerifrites (1.50€)                                                                                                                                                              
                                                                                                                                                                                                          
                    *Buffet*                                                                                                                                                                              
                      🥕 Salatbuffet überwiegend vegetarisch je 100g (1.10€)                                                                                                                              
                                                                                                                                                                                                          
                    *Gut & Günstig*                                                                                                                                                                       
                      🥩 Alaska -Seelachs -Gemüseragout mit Reis (3.60€)                                                                                                                                  
                      🌱 Soja-Ragout mit Reis (3.60€)                                                                                                                                                     
                                                                                                                                                                                                          
                    *Wahlessen 1*                                                                                                                                                                         
                      🌱 Linsen-Kokos-Pfanne mit Currykartoffeln (3.55€)                                                                                                                                  
                      🥩 Schnitzel Bar Puten und Schweineschnitzel je 100 g in Sel                                                                                                                        
           INFO     Tokens: input=1325 output=34 gesamt=1359
