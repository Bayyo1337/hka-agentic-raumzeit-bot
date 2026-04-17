[16:08:39] DEBUG    Anfrage von @Noah_Richter (chat=533286058): wo unterricht professor offermann heute                                                                                                   
           DEBUG    User @Noah_Richter: wo unterricht professor offermann heute                                                                                                                           
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
                    ...]}\n\nHeutiges Datum: 2026-04-17\nNutzer-Profil: Kein Kurs hinterlegt."                                                                                                            
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "studiengang maschinenbau: konflikte 7. semester mit thermodynamik aus dem dritten semester"                                                                           
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "⚠️ *Konflikt-Analyse: MABB*\nVergleich: Semester 7 ↔️ Semester 3\nFilter: \"thermodynamik\"\n\n📅 *Mo:*\n📍 *Management und Consulting* (Gruppe MABB.7.A)\n   Zeit:   
                    09:50–11:20\n   ✅ _Keine Überschneidungen in diesem Slot._\n\n📍 *Management und Consulting* (Gruppe MABB.7.A)\n   Zeit: 11:30–13:00\n   ✅ _Keine Überschneidungen in diesem        
                    Slot._\n\n📍 *Management und Consulting* (Gruppe MABB.7.A)\n   Zeit: 14:00–15:30\n   ✅ _Keine Überschneidungen in diesem Slot._\n\n📍 *Management und Consulting* (Gruppe MABB.7.F)\n
                    Zeit: 09:50–11:20\n   ✅ _Keine Überschneidungen in diesem Slot._\n\n📍 *Management und Consulting* (Gruppe MABB.7.F)\n   Zeit: 11:30–13:00\n   ✅ _Keine Überschneidungen in diesem  
                    Slot._\n\n📍 *Management und Consulting* (Gruppe MABB.7.F)\n   Zeit: 14:00–15:30\n   ✅ _Keine Überschneidungen in diesem Slot._\n\n📍 *Management und Consulting* (Gruppe MABB.7.K)\n
                    Zeit: 09:50–11:20\n   ✅ _Keine Überschneidungen in diesem Slot._\n\n📍 *Management und Consulting* (Gruppe MABB.7.K)\n   Zeit: 11:30–13:00\n   ✅ _Keine Überschnei... [gekürzt]"    
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "studiengang maschinenbau: konflikte 7. semester mit thermodynamik aus dem dritten semester"                                                                           
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "⚠️ *Konflikt-Analyse: MABB*\nVergleich: Semester 7 ↔️ Semester 3\nFilter: \"thermodynamik\"\n\n📅 *Di:*\n📍 *Polymers* (Gruppe A, F, K, P, U)\n   Zeit: 11:30–13:00\n 
                    🔴 Konflikt mit: *Thermodynamik* [MABB.3.E]\n      (11:30–13:00 in M-102)\n\n📅 *Mi:*\n📍 *Kunststoffverarbeitung* (Gruppe A, F, K, P, U)\n   Zeit: 09:50–11:20\n   🔴 Konflikt mit:  
                    *Thermodynamik* [MABB.3.E]\n      (09:50–11:20 in M-102)"                                                                                                                             
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "studiengang maschinenbau: konflikte 7. semester mit thermodynamik aus dem dritten semester"                                                                           
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "assistant",                                                                                                                                                              
                        "content": "⚠️ *Konflikt-Analyse: MABB*\nVergleich: Semester 7 ↔️ Semester 3\nFilter: \"thermodynamik\"\n\n📅 *Di:*\n📍 *Polymers*\n   Zeit: 11:30–13:00\n   🔴 Konflikt mit:     
                    *Thermodynamik* [MABB.3.E]\n      (11:30–13:00 in M-102)\n\n📅 *Mi:*\n📍 *Kunststoffverarbeitung*\n   Zeit: 09:50–11:20\n   🔴 Konflikt mit: *Thermodynamik* [MABB.3.E]\n             
                    (09:50–11:20 in M-102)"                                                                                                                                                               
                      },                                                                                                                                                                                  
                      {                                                                                                                                                                                   
                        "role": "user",                                                                                                                                                                   
                        "content": "wo unterricht professor offermann heute"                                                                                                                              
                      }                                                                                                                                                                                   
                    ]                                                                                                                                                                                     
[16:08:40] DEBUG    LLM Extraktion: {"calls": [{"tool": "get_lecturer_timetable", "args": {"account": "Offermann", "date": "2026-04-17"}}]}                                                               
           DEBUG    LLM → tool: get_lecturer_timetable({'account': 'Offermann', 'date': '2026-04-17'})                                                                                                    
           INFO     Dozenten-Index geladen: 457 Einträge                                                                                                                                                  
           DEBUG    API → GET /timetables/lecturer/ofpe0001                                                                                                                                               
           DEBUG    API ← 200  (139418 bytes)                                                                                                                                                             
           DEBUG    Bot Antwort: 👤 *Stundenplan Prof. Dr.-Ing. Peter Offermann* – Fr, 17.04.2026                                                                                                         
                    📧 peter.offermann@h-ka.de                                                                                                                                                            
                    🕒 *Sprechzeit:* nach Vereinbarung                                                                                                                                                    
                                                                                                                                                                                                          
                    🏫 *LI-145, LI-146* – Fr, 17.04.2026                                                                                                                                                  
                    🟢 08:00–11:30 frei                                                                                                                                                                   
                    🔴 11:30–13:00 *Automatisierungssysteme*                                                                                                                                              
                    🔴 11:30–13:00 *Automatisierungssysteme*                                                                                                                                              
                    🔴 11:30–13:00 *Automatisierungssysteme*                                                                                                                                              
                    🔴 11:30–13:00 *Automatisierungssysteme*                                                                                                                                              
                    🔴 11:30–13:00 *Automatisierungssysteme*                                                                                                                                              
                    🟢 13:00–20:00 frei                                                                                                                                                                   
                                                                                                                                                                                                          
                    🏫 *M-002* – Fr, 17.04.2026                                                                                                                                                           
                    🟢 08:00–09:50 frei                                                                                                                                                                   
                    🔴 09:50–11:20 *Elektrotechnik und elektrische Antriebe                                                                                                                               
           INFO     Tokens: input=1789 output=44 gesamt=1833

dies soll so nicht sein, wenn ein modul gleich heißt und im gleichen Block ist, muss es nicht mehrfach angezeigt werden. Dies wird wahrscheinlich an den verschiedenen Gruppen von MABB.6 liegen 

## Lösung
Deduplizierung für Dozenten-Stundenpläne optimiert.

### Fixes
1. **iCal Parser**: Befüllt nun das Feld `module` als Fallback aus dem Modulnamen.
2. **Formatter**: Dedupliziert nun auch korrekt, wenn nur der Modulname (statt des Modul-Kürzels) vorhanden ist.

**Status: ✅ Gelöst.**
