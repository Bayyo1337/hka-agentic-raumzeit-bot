# 📝 Changelog: HKA Raumzeit KI-Agent

## [17.04.2026] - Performance & Bot-Stabilität
### Added
- **Admin**: Implementierung eines nicht-blockierenden Hintergrund-Syncs für Telegram (`/sync`), um Timeouts zu vermeiden.
- **Tools**: Fortschritts-Logging während des Synchronisationsprozesses hinzugefügt.
- **Architektur**: Migration interner Agenten-Daten nach `.gemini/` und Dokumentation abgeschlossener Aufgaben in `issues/done/`.

### Fixed
- **Bot**: Automatische Aufteilung langer Nachrichten in Chunks (Chunking), um den Telegram `BadRequest: message is too long` Fehler bei umfangreichen Plänen zu beheben.
- **Konflikt-Analyse (`/setcourse`)**:
  - Filterung nun sowohl im Basis- als auch im Ziel-Semester möglich.
  - Radikale Normalisierung für robustere Vergleiche bei Kursnamen.
  - Ausblendung von Gruppennamen, wenn alle Gruppen eines Moduls betroffen sind (verbesserte Übersicht).
  - Deduplizierung und verbesserte Filterung der Ergebnisausgabe.
  - Fix für die Race-Condition beim Token-Abruf ("Keine Vorlesungen gefunden") durch Implementierung eines Auth-Locks.
- **Stundenpläne**:
  - Dozenten-Stundenpläne werden nun strikt chronologisch sortiert.
  - Deduplizierung von Modul-Einträgen in der Dozenten-Ansicht.
- **Tools**:
  - Performance-Optimierung des Personen-Sync-Regex zur Vermeidung von Backtracking.
  - Intelligentere Kursnamen-Erkennung (Bachelor-Präferenz, LongName Matching).
  - Zuverlässigeres Scraping von Büros und Kontaktdaten im Dozenten-Index.

### Changed
- Bereinigung von temporären Feedback-Dateien und Aktualisierung des internen Session-Logs.

---

## [16.04.2026] - Stabilität & Dozenten-Infos
### Fixed
- **Mensa-Integration**: Kompletter Rewrite des Scrapers für `api.mensa-ka.de`.
  - Wechsel von altem JSON-Endpunkt auf neues **GraphQL-Schema**.
  - Korrektur der Preisberechnung (Cent -> Euro).
  - Robustes Handling von `null`-Antworten bei geschlossener Mensa.
  - Direkte Integration von Allergenen und vegan/vegetarisch Flags.
- **Bot-Anzeige**:
  - Wiederherstellung des Quellcode-Links (GitHub) und des AGPL-3.0 Lizenzhinweises in der `/start`-Nachricht.
  - Fix in `formatter.py`: Kopfzeilen (Email, Sprechzeit) werden nun zuverlässig bei Dozenten-Abfragen angezeigt.
- **Dozenten-Scraper**:
  - Regex-Update für `h-ka.de` Profile, um Sprechzeiten trotz CMS-Strukturänderungen wieder zuverlässig zu finden.
  - Unterstützt nun Varianten wie "Sprechstunde", "Sprechzeiten", "Sprechstunden" (Singular/Plural).

### Changed
- Manueller Refresh des Dozenten-Index für Schlüsselpersonen (z.B. Prof. Offermann), um sofortige Verfügbarkeit der Sprechzeiten sicherzustellen.

---

## [11.04.2026] - Feature-Update
- Implementierung der intelligenten Campus-Karten.
- Stornierungs-Erkennung in der HKA-API.
- Multi-Select Support für `/setcourse`.
