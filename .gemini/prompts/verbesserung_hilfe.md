# Verbesserung: Harmonisierung und Erweiterung der Bot-Hilfe

## Hintergrund & Motivation
Nutzer und Admins finden die aktuellen Hilfe-Texte zu oberflächlich und teilweise redundant. Wichtige Parameter für Befehle wie `/sync` oder `/loglevel` sind nicht dokumentiert. Zudem fehlt die Konsistenz zwischen `/start`, `/help` und `/admin`.

## Ursachenanalyse / Ist-Zustand
- `/start` gibt zu viel redundante Information aus (doppelte Hilfe).
- Die Befehlserklärungen sind Einzeiler ohne Parameter-Hinweise.
- Neu hinzugefügte Befehle (`/bug`, `/mensa`) sind nicht in allen Hilfe-Sektionen integriert.

## Lösungsvorschlag
1. **Strukturierte Hilfe (`_command_help`):** Überarbeitung der zentralen Hilfe-Funktion. Unterteilung in "Allgemein", "Studium" und "Admin" mit klaren Parameter-Beispielen.
2. **Kompakter Start (`cmd_start`):** `/start` soll nur noch die absolut wichtigsten Beispiele und einen Link zu `/help` zeigen, anstatt die volle Hilfe zu dumpen.
3. **Erklärender Admin-Bereich:** `/admin` soll neben den Statistiken auch kurze Erklärungen zu den Admin-Tools liefern.

## Umsetzungsschritte

### 1. `src/bot.py`
- **`_command_help`**: 
    - Parameter-Hinweise hinzufügen (z.B. `/setcourse <Kurs>` - Kurs direkt speichern).
    - Neue Befehle (`/bug`, `/mensa`) integrieren.
    - Formatierung verbessern (fettgedruckte Parameter).
- **`cmd_start`**: Redundanz entfernen, Text straffen.
- **`cmd_help`**: Nutzt die neue `_command_help`.

### 2. `src/admin.py`
- **`cmd_admin`**: Die Ausgabe um eine Sektion "Schnellzugriff" erweitern, die die wichtigsten Befehle kurz erklärt.

## Verifizierung & Testing
1. Manueller Aufruf von `/start`, `/help` und `/admin`.
2. Prüfung der Formatierung (Markdown-Integrität).
