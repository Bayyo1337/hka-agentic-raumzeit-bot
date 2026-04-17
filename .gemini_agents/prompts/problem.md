# Optimierung der Konflikt-Analyse-Ausgabe

## Hintergrund & Motivation
Die aktuelle Ausgabe der Konflikt-Analyse ist redundant und zu umfangreich. Nutzer beschweren sich darüber, dass:
1. Identische Vorlesungsslots für verschiedene Gruppen (.A, .F, .U etc.) mehrfach gelistet werden.
2. Slots ohne Konflikte ("Keine Überschneidungen") angezeigt werden, was die Nachricht unnötig in die Länge zieht.

## Ursachenanalyse / Ist-Zustand
Das Ergebnis des Repro-Skripts zeigt:
```
📅 *Mo:*
📍 *Management and Consulting* (Gruppe MABB.7.A)
   Zeit: 09:50–11:20
   ✅ _Keine Überschneidungen in diesem Slot._

📍 *Management and Consulting* (Gruppe MABB.7.F)
   Zeit: 09:50–11:20
   ✅ _Keine Überschneidungen in diesem Slot._
```
Hier sind beide Probleme sichtbar: Redundanz der Gruppen und unnötige "Erfolgsmeldungen".

## Lösungsvorschlag
Die Funktion `_fmt_conflicts` in `src/formatter.py` muss angepasst werden:
1. **Deduplizierung**: Vorlesungen mit gleichem Namen, Datum und Zeit sollten zusammengefasst werden. Die Gruppen können in Klammern aufgezählt werden (z.B. "Gruppe A, F, U").
2. **Filterung**: Nur Slots, die tatsächlich mindestens einen Konflikt haben, sollen ausgegeben werden.
3. **Spezialfall**: Falls gar keine Konflikte gefunden wurden (nach der Filterung), sollte eine zusammenfassende Erfolgsmeldung ausgegeben werden.

## Umsetzungsschritte
1. **`src/formatter.py` bearbeiten**:
   - `_fmt_conflicts` umschreiben.
   - Logik zur Gruppierung nach (Name, Datum, Zeit) implementieren.
   - Filter für `if conflicts:` hinzufügen.
   - Behandlung für den Fall "Keine Konflikte nach Filterung" ergänzen.

## Verifizierung & Testing
- Ausführen des Repro-Skripts `scripts/repro_issue.py` (erwarteter Erfolg nach Fix).
- Testen mit einem Szenario, in dem tatsächlich gar keine Konflikte vorliegen.
