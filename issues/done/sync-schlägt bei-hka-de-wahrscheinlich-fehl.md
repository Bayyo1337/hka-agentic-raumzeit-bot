raumzeit> [16:43:34] INFO     Kurs-Index: Aufbau gestartet...                                                                                                                                                       
           INFO     Kurs-Index: 64 Studiengänge gefunden                                                                                                                                                  
           INFO     Kurs-Index: Prüfe Basis-Semester (Phase 1/2)...                                                                                                                                       
           DEBUG    Neues JWT geholt, läuft ab in 15983999s                                                                                                                                               
[16:43:35] INFO     Kurs-Index: Phase 1 Fortschritt: 40/640 Kombinationen geprüft                                                                                                                         
[16:43:36] INFO     Kurs-Index: Phase 1 Fortschritt: 200/640 Kombinationen geprüft                                                                                                                        
[16:43:39] INFO     Kurs-Index: Phase 1 Fortschritt: 360/640 Kombinationen geprüft                                                                                                                        
[16:43:41] INFO     Kurs-Index: Phase 1 Fortschritt: 520/640 Kombinationen geprüft                                                                                                                        
[16:43:43] INFO     Kurs-Index: 109 gültige Semester-Kombinationen gefunden                                                                                                                               
           INFO     Kurs-Index: Prüfe Gruppen-Kombinationen (Phase 2/2)...                                                                                                                                
           INFO     Kurs-Index: Phase 2 Fortschritt: 40/4142 Kombinationen geprüft                                                                                                                        
[16:43:47] INFO     Kurs-Index: Phase 2 Fortschritt: 440/4142 Kombinationen geprüft                                                                                                                       
[16:43:51] INFO     Kurs-Index: Phase 2 Fortschritt: 840/4142 Kombinationen geprüft                                                                                                                       
[16:43:54] INFO     Kurs-Index: Phase 2 Fortschritt: 1240/4142 Kombinationen geprüft                                                                                                                      
[16:43:58] INFO     Kurs-Index: Phase 2 Fortschritt: 1640/4142 Kombinationen geprüft                                                                                                                      
[16:44:02] INFO     Kurs-Index: Phase 2 Fortschritt: 2040/4142 Kombinationen geprüft                                                                                                                      
[16:44:05] INFO     Kurs-Index: Phase 2 Fortschritt: 2440/4142 Kombinationen geprüft                                                                                                                      
[16:44:11] INFO     Kurs-Index: Phase 2 Fortschritt: 2840/4142 Kombinationen geprüft                                                                                                                      
[16:44:14] INFO     Kurs-Index: Phase 2 Fortschritt: 3240/4142 Kombinationen geprüft                                                                                                                      
[16:44:18] INFO     Kurs-Index: Phase 2 Fortschritt: 3640/4142 Kombinationen geprüft                                                                                                                      
[16:44:22] INFO     Kurs-Index: Phase 2 Fortschritt: 4040/4142 Kombinationen geprüft                                                                                                                      
           INFO     Kurs-Index: 152 Einträge gespeichert                                                                                                                                                  
[16:44:23] INFO     Dozenten-Index: Sammle Kürzel aus Kursen und Räumen...                                                                                                                                
           INFO     Dozenten-Index: Kurse scannen: 40/448 abgeschlossen                                                                                                                                   
[16:44:25] INFO     Dozenten-Index: Kurse scannen: 200/448 abgeschlossen                                                                                                                                  
[16:44:28] INFO     Dozenten-Index: Kurse scannen: 360/448 abgeschlossen                                                                                                                                  
[16:44:30] INFO     Dozenten-Index: Räume scannen: 40/449 abgeschlossen                                                                                                                                   
[16:44:35] INFO     Dozenten-Index: Räume scannen: 200/449 abgeschlossen                                                                                                                                  
[16:44:40] INFO     Dozenten-Index: Räume scannen: 360/449 abgeschlossen                                                                                                                                  
[16:44:43] INFO     Dozenten-Index: 508 eindeutige Kürzel aus Raumzeit gesammelt                                                                                                                          
           INFO     Dozenten-Index: h-ka.de: Seite 1 geladen... 

## Lösung
Das Problem lag an einem ineffizienten Regulären Ausdruck in `src/tools.py`, der auf die ca. 300KB großen HTML-Seiten von `h-ka.de` angewendet wurde. Durch Catastrophic Backtracking bei fehlenden Feldern (wie `person__user-name-title`) wurde der Sync-Prozess blockiert.

**Fix:**
- Umstellung auf ein zweistufiges Verfahren: Splitten des HTML in `<tr>` Blöcke und anschließende Extraktion mit einfachen Patterns.
- Performance-Gewinn: Die Extraktion von Seite 1 sank von mehreren Minuten auf **0.0024s**.
- Robustheit: Fehlende Felder führen nicht mehr zum Backtracking.
