# Issue: togglepersonal Admin-Feature

## Problem
Es fehlte die Möglichkeit für Admins, das Personalisierungs-Feature (Speichern von Kursen, persönlicher Plan) global an- und auszuschalten.

## Lösung
1. **Admin-Kommando**: In `src/admin.py` wurde der Befehl `/togglepersonal` implementiert. Er schaltet den Status in `src/state.py (_personal_features)` um.
2. **UI-Integration**:
    - Der Bot prüft bei `/setcourse` und `/myplan` nun den globalen Status.
    - Die Hilfe-Anzeige (`/help`) blendet diese Befehle dynamisch aus, wenn das Feature deaktiviert ist.
3. **Erweiterung**: Analog wurde auch `/togglemap` für das Lageplan-Feature implementiert.

## Verifizierung
- Admin-Rechteprüfung sichergestellt durch `@_require_admin`.
- Dynamische Hilfe-Generierung erfolgreich getestet.
- Feature-Blockierung in `cmd_myplan` und `cmd_setcourse` implementiert.
