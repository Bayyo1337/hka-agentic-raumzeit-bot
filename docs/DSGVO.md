# 🌌 Datenschutzerklärung (HKA Raumzeit KI-Agent)

Stand: 11.04.2026

Diese Datenschutzerklärung informiert dich darüber, wie der HKA Raumzeit Bot deine personenbezogenen Daten verarbeitet, welche Rechte du hast und wie du die Kontrolle über deine Daten behältst.

## 1. Verantwortlicher
Der Bot wird privat betrieben. Da es sich um ein Open-Source-Projekt handelt, liegt die Datenhoheit bei der Instanz, die den Bot hostet (in diesem Fall @Bayyo1337).

## 2. Welche Daten wir speichern (Dateninventar)

Wir speichern nur Daten, die technisch notwendig sind, um dir die Funktionen des Bots anzubieten (Datenminimierung).

| Datentyp | Speicherort | Zweck | Aufbewahrung (Standard) |
| :--- | :--- | :--- | :--- |
| Telegram ID | `state.db` | Eindeutige Identifizierung | Bis zur Löschung |
| Vorname / Nutzername | `state.db` | Personalisierte Ansprache | Bis zur Löschung |
| Gewählte Kurse | `state.db` | `/myplan` Personalisierung | Bis zur Löschung |
| Chat-Historie | `state.db` | KI-Kontext (Verständnis) | 7 Tage (einstellbar) |
| Token-Verbrauch | `state.db` | Nutzungsstatistik | Bis zur Löschung |
| Zeitstempel Anfragen | `telemetry.db`| Rate-Limiting / Missbrauchsschutz | 24 Stunden (einstellbar) |
| Fehlerberichte (JSON) | `data/feedback/`| Fehlerbehebung | 30 Tage (einstellbar) |

## 3. Datenverarbeitung durch KI-Modelle
Wenn du eine natürliche Frage stellst, senden wir den Text an einen KI-Provider (z.B. Mistral AI oder OpenAI).
- **Redaktion:** Wir führen eine "Best-Effort" Redaktion (Schwärzung) von E-Mails, Telefonnummern und IBANs durch, bevor Daten an die KI gesendet oder als Fehlerbericht gespeichert werden. Es gibt keine absolute Garantie auf vollständige Anonymisierung.
- **Transparenz:** Du kannst die KI-Verarbeitung sowie die Erstellung von Fehlerberichten (`allow_error_reports`) jederzeit via `/consent` deaktivieren. Der Bot funktioniert dann nur noch eingeschränkt.
- **Telemetrie-Opt-Out:** Wenn die Telemetrie via `/consent` deaktiviert wird, werden keine Zeitstempel in der `telemetry.db` gespeichert. Das Rate-Limiting wird für den betreffenden Nutzer ausgesetzt (Bypass).

## 4. Deine Rechte (DSGVO)
Der Bot bietet integrierte Werkzeuge, um deine Rechte wahrzunehmen:
- **Auskunft (Art. 15):** Nutze `/data` für eine Übersicht.
- **Datenübertragbarkeit (Art. 20):** Nutze `/export`, um alle Daten als JSON zu erhalten.
- **Löschung (Art. 17):** Nutze `/delete`, um alle deine Daten unwiderruflich zu entfernen.
- **Einschränkung (Art. 18):** Nutze `/consent`, um einzelne Verarbeitungen zu stoppen.

## 5. Sicherheit
- Die Datenbanken sind nur lokal auf dem Server zugänglich.
- Logs werden regelmäßig rotiert und enthalten keine vollständigen Nachrichteninhalte (außer im expliziten Debug-Modus).
- Wir speichern keine Passwörter oder hochsensiblen Daten.

## 6. Kontakt
Bei Fragen zum Datenschutz wende dich bitte an den Bot-Entwickler oder erstelle ein Issue im GitHub-Repository.
