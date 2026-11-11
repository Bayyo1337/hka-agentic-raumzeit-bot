# Was wurde verändert?

Diese Dokumentation erklärt die bisher umgesetzten Änderungen am Bot in
verständlicher Sprache. Der Schwerpunkt liegt darauf, **was vorher
problematisch war**, **was jetzt anders läuft** und **welchen praktischen
Vorteil das bringt**.

## Kurzfassung

Eindeutige Raum- und Kursanfragen werden jetzt möglichst direkt und
vorhersehbar verarbeitet. Der Bot muss für solche Fragen nicht mehr zuerst ein
Sprachmodell fragen, welches Werkzeug gemeint ist.

Außerdem wurden feste Datenverträge, validierte Parser und ein speicherbarer
Klärungszustand ergänzt. Dadurch werden externe Daten kontrollierter
verarbeitet und Fehler nicht mehr so leicht als scheinbar gültige leere
Antwort dargestellt.

## Das Problem vorher

Eine einfache Anfrage wie:

> Wann ist M-102 morgen frei?

lief vorher grundsätzlich über mehrere lose gekoppelte Schritte:

```text
Nachricht
  → Router
  → Sprachmodell
  → Tool-Auswahl
  → Raumzeit-API
  → Formatter
  → Telegram-Antwort
```

Das ist für eine eindeutig erkennbare Raumnummer unnötig kompliziert. Jeder
zusätzliche Schritt kann eine weitere Fehlerquelle sein:

- Das Sprachmodell kann das falsche Tool wählen.
- Ein Modell- oder API-Ausfall kann eine eigentlich einfache Frage blockieren.
- Parameter können unterschiedlich geschrieben oder unvollständig sein.
- Beliebige Dictionaries erschweren es, Fehler und gültige Ergebnisse
  auseinanderzuhalten.
- Zwischenfragen lagen teilweise nur im Arbeitsspeicher und waren nach einem
  Neustart verloren.

## 1. Direkte Raum- und Kursanfragen

### Was wurde geändert?

Der Agent erkennt eindeutige Eingaben jetzt selbst:

- Räume wie `M-102`
- Kurs-Keys wie `MABB.6`
- ausgeschriebene Varianten wie `MABB 6` oder `MABB-6`

Bei einer solchen Eingabe wird direkt das passende bestehende Tool
aufgerufen. Das Sprachmodell wird nur noch für Anfragen benötigt, bei denen
die Absicht oder die Parameter tatsächlich unklar sind.

### Was repariert das?

Eine eindeutige Raumfrage wird nicht mehr von einer freien Modellentscheidung
abhängig gemacht. Der Bot kann nicht mehr versehentlich ein Mensa-, Dozenten-
oder Karten-Tool auswählen, obwohl eindeutig ein Raum gemeint ist.

### Warum ist das besser?

- schnellere Antworten;
- weniger unnötige LLM-Aufrufe;
- geringere Kosten;
- reproduzierbares Verhalten;
- funktioniert auch dann, wenn der LLM-Dienst gerade nicht erreichbar ist.

Der Ablauf sieht nun für eindeutige Fälle so aus:

```text
Nachricht
  → Raum/Kurs erkennen
  → Parameter normalisieren
  → passendes Tool ausführen
  → Antwort formatieren
```

## 2. Einheitliche Datumsverarbeitung

### Was wurde geändert?

Relative und konkrete Datumsangaben werden zentral erkannt:

- „heute“
- „morgen“
- „gestern“
- `09.11.2026`
- `2026-11-09`

Das Datum wird vor dem API-Aufruf in ein einheitliches Format
`YYYY-MM-DD` umgewandelt.

### Was repariert das?

Vorher konnten verschiedene Pfade Datumsangaben unterschiedlich interpretieren
oder an das Sprachmodell delegieren. Dadurch bestand das Risiko, dass ein
falscher Tag abgefragt oder ein optionaler Parameter uneinheitlich behandelt
wird.

### Warum ist das besser?

Die gleiche Eingabe erzeugt unter denselben Bedingungen denselben API-Parameter.
Das macht die Verarbeitung nachvollziehbar und leichter testbar.

## 3. Feste Datenmodelle statt beliebiger Dictionaries

### Was wurde geändert?

Für zentrale Objekte wurden typisierte Modelle ergänzt, unter anderem für:

- Termine;
- Stundenplan-Ergebnisse;
- Anfragen;
- Pipeline-Abläufe;
- Fehlercodes;
- Personen;
- Mensa-Gerichte;
- Gesprächszustände;
- Status und Zeitpunkt einer externen Datenquelle.

### Was repariert das?

Früher konnten verschiedene Funktionen für dasselbe Feld unterschiedliche
Namen oder Datentypen verwenden. Ein fehlendes Feld wurde dann leicht erst
spät entdeckt oder als leere Antwort behandelt.

### Warum ist das besser?

Die Software erkennt viele fehlerhafte Daten früher. Außerdem ist klar
definiert, welche Informationen ein Adapter oder Use-Case liefert. Das
reduziert Sonderfälle und macht spätere Erweiterungen sicherer.

## 4. Bestehende Tools werden kontrolliert angebunden

### Was wurde geändert?

Die vorhandenen Raumzeit-Tools wurden nicht sofort ersetzt. Stattdessen gibt es
eine Übersetzungsschicht, die alte Tool-Ergebnisse in das neue strukturierte
Terminmodell überführt.

### Was repariert das?

Ein kompletter Umbau auf einmal wäre riskant gewesen. Ohne diese
Übersetzungsschicht hätten alte und neue Architektur nicht gemeinsam betrieben
werden können.

### Warum ist das besser?

Der neue deterministische Kern kann bereits genutzt und getestet werden,
während die bestehende API-Implementierung schrittweise ersetzt werden kann.
Das verringert das Risiko eines großen, unkontrollierten Umstiegs.

## 5. Gesprächszustand wird speicherbar

### Was wurde geändert?

Für Rückfragen gibt es jetzt ein explizites Modell und eine SQLite-Anbindung.
Gespeichert werden können beispielsweise:

- der aktuelle Intent;
- bereits erkannte Entitäten;
- die noch fehlende Information;
- die ursprüngliche Anfrage;
- die Anzahl der Klärungsversuche;
- ein Ablaufzeitpunkt.

Die vorhandene Datenbankinitialisierung legt dafür ebenfalls eine Tabelle an.

### Was repariert das?

Ein Dialogzustand war vorher teilweise nur im Speicher vorhanden. Nach einem
Neustart konnte der Bot dadurch nicht mehr wissen, worauf sich die Antwort des
Nutzers bezog.

### Warum ist das besser?

Rückfragen werden zu einem nachvollziehbaren Zustand statt zu einer versteckten
Sonderlogik. Das ist robuster bei Neustarts und bildet die Grundlage für
kontrollierte Ablaufzeiten und begrenzte Klärungsversuche.

## 6. Kontrollierte Parser für HKA und Mensa

### HKA-Personen

HTML-Daten von HKA-Personen werden in ein `Person`-Modell übersetzt. Namen und
E-Mail-Adressen werden bereinigt; unvollständige Datensätze werden nicht
still als gültige Personen weitergereicht.

### Mensa

Mensa-Gerichte werden in ein `Meal`-Modell übersetzt. Dabei werden unter
anderem ID, Name, Preis, Allergene, Zusatzstoffe sowie Vegan-/Vegetarisch-
Angaben geprüft.

### Was repariert das?

Externe Antworten sind nicht immer vollständig oder exakt so aufgebaut wie
erwartet. Vorher konnten solche Abweichungen später in der Verarbeitung zu
unklaren Fehlern führen.

### Warum ist das besser?

Fehler an der Quelle werden direkt als Quellenfehler erkennbar. Gültige Daten
bleiben von ungültigen Daten getrennt, statt dass ein fehlerhafter Datensatz
eine scheinbar erfolgreiche Antwort erzeugt.

## 7. Robustere Telegram-Ausgabe

Die Präsentationsschicht maskiert problematische Markdown-Zeichen wie:

- `_`
- `*`
- `` ` ``
- `[`

Lange Texte können außerdem in Telegram-gerechte Abschnitte geteilt werden.
Damit sinkt das Risiko, dass Namen, Kurs-Keys oder Modulbezeichnungen eine
Telegram-Fehlermeldung wie „Can't parse entities“ auslösen.

## 8. Tests

Für die neuen Bestandteile wurden fokussierte Tests ergänzt. Sie prüfen unter
anderem:

- Erkennung von Räumen und Kursen;
- Auflösung relativer und konkreter Daten;
- direkte Tool-Ausführung ohne LLM;
- Übersetzung alter Tool-Ergebnisse;
- Speicherung und Laden von Gesprächszuständen;
- HKA- und Mensa-Parser;
- Datenverträge und Fehlerfälle;
- Markdown-Escaping und Telegram-Chunking.

Der fokussierte Testlauf umfasst aktuell **17 erfolgreiche Tests**.

## Was dadurch insgesamt besser funktioniert

Die Verarbeitung wird für eindeutige Anfragen:

- **schneller**, weil unnötige LLM-Schritte entfallen;
- **verlässlicher**, weil Tools nicht frei geraten werden;
- **reproduzierbarer**, weil Parameter deterministisch normalisiert werden;
- **wartbarer**, weil zentrale Daten typisiert sind;
- **fehlertoleranter**, weil externe Antworten validiert werden;
- **robuster bei Neustarts**, weil Klärungszustände gespeichert werden;
- **sicherer für Telegram**, weil Markdown korrekt escaped wird.

## Was noch nicht vollständig umgesetzt ist

Diese Änderungen bilden den neuen Kern und arbeiten noch mit der bestehenden
Bot-Architektur zusammen. Der vollständige Greenfield-Neuaufbau aus
`docs/REBUILD_PLAN.md` ist damit noch nicht abgeschlossen.

Noch offen beziehungsweise außerhalb dieser Repository-Sitzung sind:

- vollständiger Ersatz aller alten Telegram- und LLM-Pfade;
- produktiver Parallelbetrieb von alter und neuer Bot-Version;
- Vergleich über echte Telegram-Chats und externe API-Daten;
- Datenmigration für einen produktiven Umstieg;
- ein vollständiger E2E-Lauf mit echten Zugangsdaten und Netzwerkzugriff.

Der aktuelle Stand ist deshalb am besten als **sicher integrierter,
deterministischer Architekturkern** zu verstehen, nicht als bereits vollständig
abgeschlossene Produktionsmigration.
