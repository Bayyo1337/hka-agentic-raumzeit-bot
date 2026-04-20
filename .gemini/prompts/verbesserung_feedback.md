# Verbesserung: Interaktives Feedback & Bug-Reporting System

## Hintergrund & Motivation
Nutzer möchten Fehler oder Feedback direkt als `active issue` im Repository melden können (ähnlich dem System, das Admins bei Abstürzen nutzen). Dabei soll der Kontext (die letzten Befehle) einbezogen werden, ein eigener Titel vergeben und ein zusätzlicher Kommentar hinzugefügt werden können.

## Ursachenanalyse / Ist-Zustand
- `/feedback` ist aktuell ein Admin-Befehl zum Auflisten von Feedback-Files.
- Es gibt keinen geführten Prozess für Nutzer, um strukturierte Issues zu erstellen.
- Die Historie wird zwar in der DB gespeichert, aber bisher nicht für das Reporting genutzt.

## Lösungsvorschlag
1. **Neuer Befehl `/bug`**: Startet einen interaktiven Prozess für alle Nutzer.
2. **Multi-Step Workflow**:
   - **Step 1: Titel**: Bot bittet um einen kurzen Titel (wird der Dateiname).
   - **Step 2: Kontext-Auswahl**: Bot zeigt die letzten 5 Befehle des Nutzers mit Inline-Buttons an. Der Nutzer kann einen auswählen oder "Kein Kontext" klicken.
   - **Step 3: Kommentar**: Bot fragt nach einer detaillierten Beschreibung.
   - **Step 4: Generierung**: Bot erstellt die `.md` Datei in `issues/active/` und informiert den Nutzer.

## Umsetzungsschritte

### 1. `src/bot.py`
- **Conversation State**: Wir brauchen Zustände für `WAITING_FOR_TITLE`, `WAITING_FOR_CONTEXT` und `WAITING_FOR_COMMENT`.
- **`cmd_bug`**: Initialisiert die Konversation.
- **`handle_message`**: Muss prüfen, ob ein Feedback-Prozess aktiv ist.
- **`handle_callback`**: Muss Kontext-Auswahl verarbeiten.

### 2. `src/admin.py`
- Neue Hilfsfunktion `save_user_issue(title, context_cmd, comment, user_info)` implementieren.
- Diese Funktion baut das Markdown-Dokument zusammen und speichert es.

## Verifizierung & Testing
1. Manueller Test des `/bug` Befehls.
2. Prüfung, ob die Datei in `issues/active/` mit dem gewählten Namen und Inhalt korrekt angelegt wurde.
3. Repro-Skript `scripts/repro_feedback_history.py` (bereits erfolgreich getestet) als Basis für die Historien-Logik.
