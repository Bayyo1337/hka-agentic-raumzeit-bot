# 📝 Changelog: HKA Raumzeit KI-Agent

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
