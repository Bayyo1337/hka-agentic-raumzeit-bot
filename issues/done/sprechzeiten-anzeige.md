
## Lösung
Dozenten-Sprechzeiten und Kontaktinfos wurden verbessert.

### Änderungen
- **Scraper**: Der h-ka.de Scraper ist nun robuster und findet Dozenten auch ohne Titel.
- **Sprechzeiten**: Das Regex-Pattern wurde flexibler gestaltet, um mehr Varianten der h-ka.de Profile zu erfassen.
- **Matching**: Dozenten ohne direktes Raumzeit-Kürzel werden nun über ihr E-Mail-Präfix gematcht, damit sie im Index auftauchen.
- **Zusatzinfos**: Es wird nun auch das Büro/Raum aus dem h-ka.de Profil extrahiert und im Bot angezeigt.

**Status: ✅ Gelöst.**
