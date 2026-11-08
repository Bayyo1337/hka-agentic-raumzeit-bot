# Neuaufbauplan: HKA Raumzeit Bot

## 1. Ziel dieses Dokuments

Dieses Dokument beschreibt den vollständigen fachlichen Umfang des aktuellen
Repos sowie einen Plan für einen klareren, zuverlässigeren Neubau. Es ist kein
Plan für weitere Einzelpatches an der bestehenden Struktur. Der empfohlene Weg
ist ein Greenfield-Neubau mit einer zeitweise parallel betriebenen alten
Version.

Der Bot soll Studierenden verlässliche Antworten zu Raumzeit, Stundenplänen,
Dozenten, Mensa und Campus-Orten geben. Das Sprachmodell darf Absichten und
fehlende Parameter erkennen, aber weder Fakten erfinden noch die endgültige
Antwort formulieren.

### Verbindliches Leitprinzip: Deterministic First

Der Neubau ist nur dann erfolgreich, wenn möglichst viel Verhalten außerhalb
des LLM reproduzierbar implementiert ist. Das LLM ist kein Agent mit freier
Tool-Auswahl und kein Antwortgenerator, sondern ein kontrollierter
Sprach-Übersetzer:

```text
Natürliche Sprache
  → LLM: Intent + erkannte Roh-Entitäten als strukturiertes JSON
  → Python: Validierung, Normalisierung und Auflösung
  → Python: Kontext aus Profil, Kalender, Katalog und Cache
  → Python: deterministischer Use-Case und Datenabruf
  → Python: validiertes Ergebnis und Antwort
```

Das LLM darf insbesondere nicht selbst entscheiden:

- welchen Endpoint es aufruft;
- welche Raum-, Kurs- oder Dozenten-ID zu einer Eingabe gehört;
- welche Datumsbereiche „nächste Woche“ oder „heute“ bedeuten;
- ob ein leeres Ergebnis ein Fehler oder ein gültiges Ergebnis ist;
- wie externe Daten zusammengeführt, dedupliziert oder priorisiert werden;
- welche Fakten oder Antworttexte an den Nutzer gesendet werden.

Bei ungültigen, fehlenden oder widersprüchlichen Angaben liefert Python eine
gezielte Rückfrage. Bei Unsicherheit wird nicht geraten. Jede LLM-Ausgabe wird
gegen ein Schema validiert und kann durch deterministische Regeln abgewiesen
werden.

---

## 2. Vollständige Produktabsicht

### 2.1 Nutzerfragen

Der Bot unterstützt diese fachlichen Anfragearten:

| Bereich | Nutzerabsicht |
|---|---|
| Raum | Belegung eines Raums für einen Tag oder eine Woche; freie Zeitfenster |
| Kurs | Stundenplan eines Studiengangs und Semesters, inklusive Gruppen |
| Persönlicher Plan | Mehrere gespeicherte Kurs-Semester zusammenführen |
| Dozent | Stundenplan, E-Mail, Büro und Sprechzeiten |
| Mensa | Speiseplan für eine Mensa und einen Tag |
| Mensa-Details | Allergene, Zusatzstoffe, Preise sowie vegan/vegetarisch |
| Konflikte | Überschneidungen zwischen zwei Semestern oder Kursplänen |
| Campus | Gebäude/Raum auf Lageplan und Stockwerk zuordnen |
| Kalender | Semesterzeiten, Prüfungszeiträume und vorlesungsfreie Zeiten |
| Hilfe | Erklären, welche Fragen und Befehle unterstützt werden |

Beispiele aus dem bestehenden Verhalten:

- „Wann ist M-102 frei?“
- „Welche Vorlesungen hat MABB 2 morgen?“
- „Was habe ich heute?“
- „Wann hat Herr Taheran Vorlesung?“
- „Wie lautet die E-Mail von Herr Taheran?“
- „Was gibt es heute in der Mensa?“
- „Welche Allergene sind in Wahlessen 2?“
- „Gibt es Überschneidungen bei Maschinenbau zwischen dem 3. und 5. Semester?“
- „Wo ist Gebäude LI?“

### 2.2 Telegram-Funktionen

#### Nutzerbefehle

- `/start`
- `/help`
- `/mensa`
- `/setcourse`
- `/myplan`
- `/stats`
- `/reset`
- `/bug`

#### Admin-Funktionen

- Status und Statistiken
- Daten-Synchronisation
- Ping und Indexalter
- Nutzer suchen, sperren und Limits setzen
- Broadcast
- Token- und Verlaufverwaltung
- Provider- und Log-Level-Verwaltung
- Wartungsmodus
- Feature-Schalter für Personalisierung und Karten
- Feedback- und Fehlerverwaltung

### 2.3 Betriebsabsicht

- Asynchroner Telegram-Bot.
- Raumzeit als primäre Datenquelle.
- Mensa als separate GraphQL-Datenquelle.
- HKA-Webseite als ergänzende Quelle für Dozentenprofile.
- Wiederholbare Synchronisation mit Fortschritt und Fehlerbericht.
- Caches dürfen die Antwort beschleunigen, aber keine veralteten Fakten
  unbemerkt als aktuell ausgeben.
- Alle Antworttexte und Markdown-Escapes werden in Python erzeugt.
- Nutzer-, Cache- und Telemetriedaten bleiben getrennt.
- Keine Secrets, Datenbanken, Logs oder Testartefakte im Git-Repository.

---

## 3. Diagnose der aktuellen Architektur

### 3.1 Hauptursachen der Unübersichtlichkeit

1. **Doppelte Entscheidungslogik:** `router.py` klassifiziert die Anfrage,
   danach entscheidet `agent.py` erneut über Tool und Parameter.
2. **Überladene `tools.py`:** Authentifizierung, HTTP-Clients, Raumauflösung,
   iCal-Parsing, HTML-Scraping, Kurs-Probing, Mensa-GraphQL, Caching,
   Tool-Definitionen und Dispatcher liegen in einer Datei.
3. **Unklare Datenverträge:** Die Adapter liefern uneinheitliche Dictionaries
   mit optionalen, teils unterschiedlich benannten Feldern.
4. **LLM als implizite Orchestrierung:** Das Modell kann mehrere Calls erzeugen,
   während Python zusätzlich Sonderlogik, Eskalationen und Formatierung
   übernimmt.
5. **Versteckter Zustand:** Pending-Bestätigungen, Fehler-Cache, Bug-Reports,
   Provider-Override und Feature-Flags liegen teilweise nur im Speicher.
6. **Fehler werden verschluckt:** Mehrere Scraper- und Cache-Pfade verwenden
   breite `except`-Blöcke oder geben bei Fehlern leere Ergebnisse zurück.
7. **Synchronisation ist zu teuer:** Kurs- und Dozenten-Indizes werden durch
   umfangreiches Probing und massenhaftes Abrufen von Kalendern aufgebaut.
8. **HTML-RegEx als Datenintegration:** Änderungen am HKA-CMS können jederzeit
   Namen, Räume oder Sprechzeiten unbemerkt unvollständig machen.
9. **Tests prüfen überwiegend den Happy Path:** Die E2E-Fälle testen Router,
   LLM, reale Tool-Kette und Text-Keywords gemeinsam; die eigentliche Fehler-
   ursache ist dadurch schwer isolierbar.
10. **Dokumentation und Code driften auseinander:** Mehrere Architekturstände
    und frühere Datenbankmodelle sind gleichzeitig dokumentiert.

### 3.2 Problemfelder im Scraping

- HKA-Personen werden per HTML-Seiten und Regex aus einer paginierten Suche
  extrahiert.
- Sprechzeiten und Räume werden aus unversioniertem HTML abgeleitet.
- Raumzeit-Kursgruppen werden durch viele HTTP-Probes erraten.
- iCal wird mit einem lokalen Minimalparser verarbeitet; Zeilenumbrüche,
  Escaping, Zeitzonen, wiederkehrende Termine und Änderungen sind nicht
  vollständig als Datenmodell abgebildet.
- API-Antworten werden je nach Endpoint als JSON oder Text/iCal interpretiert,
  teilweise erst nach fehlgeschlagenem JSON-Parsing.
- Netzwerkfehler, HTTP-Fehler, leere Daten und „Quelle liefert nichts“ sind
  nicht konsequent getrennt.

### 3.3 Problemfelder bei der Anfragebearbeitung

- Eine Anfrage kann über Regex-Routing, LLM-Routing, LLM-Extraktion,
  Tool-Dispatcher, Sonderaktionen und Formatter laufen.
- Fehlende Parameter werden nicht einheitlich erkannt; der geplante
  `pending_intent`-Mechanismus ist nicht vollständig angeschlossen.
- Kurs-„Keine Daten“-Fälle werden über einen Text-Sentinel in der Antwort
  erkannt und lösen eine mehrstufige Sonderlogik in `bot.py` aus.
- Tool-Argumente werden überwiegend über Dictionaries und Lambdas validiert.
- Ergebnisse mehrerer Tools werden nicht als fachliches Antwortmodell
  zusammengeführt, sondern der Formatter wählt im Zweifel den letzten Treffer.
- Historie enthält fertige Antworttexte, obwohl der Gesprächszustand und die
  fachlichen Ergebnisse getrennt betrachtet werden sollten.

---

## 4. Zielprinzipien für den Neubau

1. **Ein Eingang, eine Pipeline:** Jede Nachricht läuft durch denselben
   nachvollziehbaren Ablauf.
2. **Deterministische Fakten:** API-Adapter und Domänenlogik liefern Fakten;
   das LLM darf keine Fakten ergänzen.
3. **Explizite Zustände:** Anfrage, fehlende Parameter, Synchronisation und
   Fehler werden als typisierte Zustände behandelt.
4. **Adapter statt Scraper-Mischung:** Jede externe Quelle hat einen eigenen
   Adapter, Parser, Validator und Cache.
5. **Raw vor normalized:** Rohantworten können zur Diagnose gespeichert werden;
   die Bot-Logik arbeitet ausschließlich mit validierten Normalformen.
6. **Stale ist sichtbar:** Jede Antwort kennt Quelle, Abrufzeit und
   Aktualitätsstatus.
7. **Keine stillen Fallbacks:** Ein Fehler wird als Fehlerzustand ausgegeben,
   nicht als leere, erfolgreich aussehende Antwort.
8. **Ein fachlicher Vertrag:** Alle Module arbeiten mit Pydantic-Modellen oder
   äquivalenten typisierten Domain-Objekten.
9. **Testbarkeit ohne Telegram und ohne externe APIs:** Router, Parser,
   Use-Cases und Formatter werden isoliert testbar.
10. **Feature-Gates statt Sonderpfade:** Noch instabile Funktionen werden
    sichtbar deaktiviert, nicht halb ausgeführt.

---

## 5. Zielarchitektur

```text
src/
├── app/
│   ├── telegram/
│   │   ├── handlers.py
│   │   ├── commands.py
│   │   ├── callbacks.py
│   │   └── presenter.py
│   ├── requests/
│   │   ├── pipeline.py
│   │   ├── session_state.py
│   │   ├── intent.py
│   │   ├── entity_extraction.py
│   │   └── clarification.py
│   └── admin/
│       └── handlers.py
├── domain/
│   ├── models.py
│   ├── intents.py
│   ├── errors.py
│   ├── timetable.py
│   ├── meals.py
│   └── people.py
├── use_cases/
│   ├── room_timetable.py
│   ├── course_timetable.py
│   ├── personal_plan.py
│   ├── lecturer.py
│   ├── mensa.py
│   ├── conflicts.py
│   ├── campus.py
│   └── calendar.py
├── integrations/
│   ├── raumzeit/
│   │   ├── client.py
│   │   ├── auth.py
│   │   ├── timetable_api.py
│   │   ├── course_catalog.py
│   │   └── parsers.py
│   ├── hka/
│   │   ├── people_client.py
│   │   └── people_parser.py
│   └── mensa/
│       ├── client.py
│       └── graphql_models.py
├── persistence/
│   ├── database.py
│   ├── repositories.py
│   ├── migrations/
│   └── cache.py
├── presentation/
│   ├── markdown.py
│   ├── timetable.py
│   ├── mensa.py
│   └── errors.py
└── config.py
```

Die genauen Dateinamen können angepasst werden. Entscheidend ist die Trennung
zwischen Telegram, Use-Cases, Domäne, externen Quellen, Persistenz und
Präsentation.

### 5.1 Anfrage-Pipeline

```text
Telegram Update
  → Zugriff/Ban/Rate-Limit
  → Session laden
  → Intent erkennen
  → Entitäten extrahieren und normalisieren
  → Schema validieren
  → fehlende Informationen klären
  → genau einen Use-Case ausführen
  → Domain-Ergebnis erzeugen
  → typisierte Antwort rendern
  → Verlauf, Telemetrie und ggf. Cache speichern
```

#### Intent-Erkennung

Der Neubau verwendet eine einzige Routing-Komponente:

- deterministische Regeln für eindeutige Formen wie Raum-IDs, Befehle und
  Datumsmuster;
- ein einzelner LLM-Klassifikator als Fallback;
- erlaubte Intents als Enum;
- strukturierte Ausgabe mit `intent`, `confidence` und `entities`;
- keine Tool-Auswahl durch freie Modellantwort;
- bei niedriger Sicherheit eine Rückfrage statt eines geratenen Calls.

Die Ausgabe des Modells ist bewusst klein und darf keine ausführbare Aktion
enthalten:

```json
{
  "intent": "room_timetable",
  "entities": {
    "room_query": "M-102",
    "date_expression": "morgen"
  },
  "confidence": 0.94
}
```

Danach übernimmt ausschließlich Python:

| Aufgabe | Zuständigkeit |
|---|---|
| Befehle und eindeutige Muster | deterministische Regeln |
| Intent-Fallback | LLM mit Enum-Schema |
| Raum/Kurs/Dozent auflösen | lokaler Katalog und Resolver |
| Relative Datumsangaben | zentrale Datumslogik |
| Berechtigungen und Limits | Policy-Code |
| API-Auswahl | Use-Case-Mapping |
| Retries, Caching, Fallbacks | Integrationsschicht |
| Deduplizierung und Konflikte | Domain-Code |
| Antworttext und Markdown | Presenter |

#### Ausführung

Der Intent wird auf einen Use-Case gemappt. Der Use-Case erhält ein validiertes
Request-Modell und darf nur die benötigten Repositories/Adapter aufrufen.

Beispiel:

```text
RoomTimetableRequest(room="M-102", date=...)
  → RoomTimetableService
  → RaumzeitRoomRepository
  → TimetableResult
  → TimetablePresenter
```

#### Klärungszustand

Rückfragen werden als persistierter `ConversationState` gespeichert:

- aktueller Intent;
- bereits erkannte Entitäten;
- erwartete Entität;
- Ablaufzeit;
- ursprüngliche Nutzernachricht;
- Anzahl der Klärungsversuche.

Text-Sentinel wie `CONFIRM_SENTINEL` entfällt. Der Dialog entscheidet anhand
des Zustandsmodells, nicht anhand eines formatierten Antwortstrings.

---

## 6. Ziel-Datenmodell

Alle externen Daten werden in ein gemeinsames Modell überführt.

### 6.1 TimetableEvent

- `source`
- `external_id`
- `course_key`
- `group`
- `title`
- `module`
- `lecturers`
- `room`
- `date`
- `start`
- `end`
- `cancelled`
- `retrieved_at`
- `source_status`

### 6.2 Personen

- `account`
- `display_name`
- `email`
- `office`
- `office_hours`
- `profile_url`
- `source`
- `retrieved_at`

### 6.3 Mensa

- `canteen_id`
- `canteen_name`
- `date`
- `line_id`
- `line_name`
- `meal_id`
- `meal_name`
- `prices`
- `allergens`
- `additives`
- `dietary_flags`
- `retrieved_at`

### 6.4 Resultat und Fehler

Jeder Use-Case liefert entweder:

- ein typisiertes Ergebnis mit `source_status` und `retrieved_at`, oder
- einen standardisierten Fehler:
  - `not_found`
  - `invalid_input`
  - `source_unavailable`
  - `source_changed`
  - `stale_cache`
  - `no_results`
  - `permission_denied`

---

## 7. Scraping- und Datenintegrationsplan

Das Scraping ist der wichtigste technische Neuaufbau und wird nicht in der
Telegram-Anwendung nebenbei ausgeführt.

### 7.1 Gemeinsames Adapter-Protokoll

Jede Quelle bekommt:

1. `fetch()` für HTTP/GraphQL;
2. `parse()` für Rohdaten;
3. `validate()` für Pflichtfelder und Datentypen;
4. `normalize()` für das interne Modell;
5. `persist()` für Cache/Snapshot;
6. strukturierte Metriken und Fehlercodes.

### 7.2 Raumzeit-Adapter

- Einen wiederverwendbaren HTTP-Client mit Timeout, Retries,
  Rate-Limit-Verhalten und Auth-Refresh.
- JWT-Zugriff in einer dedizierten Auth-Komponente.
- JSON-Endpunkte strikt anhand von Response-Status und Content-Type behandeln.
- iCal mit einem robusten Parser oder einem klar getesteten Parser-Modul
  verarbeiten; Zeitzone, Escaping, `TZID`, `DTSTART`, `DTEND`, Änderungen und
  wiederkehrende Termine als eigene Testfälle abdecken.
- Raum-, Kurs- und Dozentenauflösung als getrennte Repositories.
- Kursgruppen nicht bei jeder Nutzeranfrage brute-forcen.
- Discovery als kontrollierter Job mit:
  - begrenzter Parallelität;
  - Backoff;
  - deduplizierten Keys;
  - Snapshot-Ergebnis;
  - Fehlerbericht pro Key;
  - Wiederaufnahme nach Abbruch.
- Wenn die API einen Katalog oder Metadaten-Endpunkt liefert, diesen immer vor
  Heuristiken und Probing verwenden.

### 7.3 HKA-Personen-Adapter

- HTML-Parsing über DOM/Selektoren statt großer Regex-Ausdrücke.
- Pagination anhand der tatsächlichen Navigationslinks.
- Profile einzeln und kontrolliert nachladen.
- Roh-HTML und Parser-Version im Snapshot protokollieren.
- Fehlende Felder als `None`, nicht als erfundene oder leere Personen.
- Parser-Contract-Tests mit gespeicherten anonymisierten HTML-Fixtures.
- Bei struktureller Änderung den Sync als `source_changed` markieren und den
  letzten validierten Snapshot behalten.

### 7.4 Mensa-Adapter

- GraphQL-Schema und Antwortmodell zentral kapseln.
- Canteen- und Meal-IDs niemals durch das LLM bestimmen lassen.
- Menü zuerst laden, danach Detailabfragen nur anhand bekannter IDs oder
  deterministischer Namenssuche aus dem Menü.
- Allergene und Zusatzstoffe beim Normalisieren dekodieren.
- Geschlossene Mensa, leeres Menü und API-Fehler unterscheiden.
- Tagescache mit expliziter Aktualitätsangabe.

### 7.5 Sync-Betrieb

Separater Sync-Runner statt versteckter Hintergrundtasks in `bot.py`:

```text
sync courses
sync lecturers
sync mensa --date YYYY-MM-DD
sync all
```

Jeder Lauf erzeugt einen Jobdatensatz mit Start, Ende, Status, Anzahl
Funde, Anzahl Fehler und Quelle. Der Bot kann den letzten erfolgreichen
Snapshot lesen, aber keinen laufenden Sync blockieren.

---

## 8. Feature-Schnitt für den Neubau

### P0: Muss stabil funktionieren

1. Raumbelegung und freie Zeitfenster.
2. Kurs-Stundenplan für einen Tag und eine Woche.
3. Dozenten-Stundenplan.
4. Dozenten-Kontaktinformationen.
5. Mensa-Tagesplan.
6. Mensa-Details und Allergene.
7. Verständliche Fehler- und Keine-Daten-Antworten.
8. Einfache Hilfe, Zugriffskontrolle, Rate-Limit und Admin-Status.

### P1: Nach stabiler Kernpipeline

1. `/setcourse` für mehrere Kurs-Semester.
2. `/myplan` mit Cache und sauberem Aktualitätsstatus.
3. Konfliktanalyse.
4. Hochschulkalender.
5. Campus-Karten und Stockwerksermittlung.
6. Feedback-/Bug-Workflow.
7. Persistenter Gesprächszustand für Rückfragen.

### P2: Bewusst nach hinten verschieben

1. Mehrere LLM-Provider und dynamischer Providerwechsel.
2. Rich-Terminal-Dashboard.
3. Automatisches Fehler-zu-Issue-Verhalten.
4. Komplexe Fuzzy-Fallbacks für halluzinierte Mensa-IDs.
5. Umfangreiche Admin-Kommandos, sofern sie nicht für den Betrieb erforderlich
   sind.

Ein P2-Feature darf erst zurückkehren, wenn sein Nutzen, Datenvertrag,
Fehlerverhalten und Testumfang definiert sind. „Historisch vorhanden“ ist
kein ausreichender Grund für die Übernahme.

---

## 9. Umsetzungsphasen

### Phase 0: Vertrag und Bestandsaufnahme

- Nutzerfälle und Befehle als akzeptierte Szenarien dokumentieren.
- Externe Endpunkte, Response-Beispiele und bekannte Einschränkungen erfassen.
- Bestehende Datenbanken nur lesend analysieren; keine Migration im laufenden
  Bot.
- Entscheidung über unterstützte Provider treffen: zunächst genau einen
  stabilen Provider.
- Abnahmekriterien für P0 festlegen.

**Gate:** Jede P0-Anfrage ist als reproduzierbarer Testfall beschrieben.

### Phase 1: Neues Grundgerüst

- Neues Paketlayout nach Zielarchitektur anlegen.
- Konfiguration mit Startvalidierung und sicheren Fehlermeldungen.
- Domain-Modelle und Fehlercodes definieren.
- Telegram-Adapter mit einem einfachen Health- und Echo-freien Handler.
- Datenbankmigrationen und Repository-Schnittstellen einführen.

**Gate:** Anwendung startet ohne externe Datenabfrage; Unit-Tests laufen
isoliert.

### Phase 2: Raumzeit-Integration

- Auth-Client und HTTP-Client.
- Raumkatalog und Raumauflösung.
- Timetable-Adapter für JSON.
- iCal-Adapter, falls für Kurs/Dozent erforderlich.
- Snapshots, Cache und Contract-Tests.

**Gate:** Raum- und Kursdaten können mit Fixture-Daten ohne Telegram
abgerufen, validiert und formatiert werden.

### Phase 3: Neue Anfragepipeline

- Intent-Enum und deterministische Vorprüfung.
- Ein strukturierter LLM-Fallback.
- Entity-Normalisierung für Raum, Kurs, Dozent, Mensa und Datum.
- Klärungszustand und Ablauf.
- Use-Case-Dispatcher ohne freie Tool-Calls.
- Test-Harness, das für identische Eingaben identische Requests und
  Antworten erzeugt.
- Ablehnungslogik für unvollständige, widersprüchliche oder nicht validierbare
  LLM-Ausgaben.

**Gate:** Jede Anfrage erzeugt einen nachvollziehbaren Pipeline-Trace:
`intent → entities → use_case → source → result → response`.

Zusätzlich gilt für dieses Gate:

- Der Use-Case-Dispatcher erhält niemals einen Tool-Namen direkt vom LLM.
- Der Use-Case entscheidet selbst über alle API-Aufrufe.
- Identische Eingabe, identischer Nutzerkontext und identischer Daten-Snapshot
  müssen dasselbe fachliche Ergebnis erzeugen.
- Ein LLM-Ausfall darf nur die Spracherkennung betreffen; er darf keine
  inkonsistente Teilantwort oder ungeprüfte API-Aktion erzeugen.

### Phase 4: Präsentation und Nutzeroberfläche

- Markdown-Renderer pro Resultattyp.
- Einheitliche Telegram-Fehlermeldungen.
- Telegram-Limit und Chunking als Presenter-Verantwortung.
- `/start`, `/help`, `/stats`, `/reset`.
- Keine Antworttexte aus dem LLM übernehmen.

**Gate:** Snapshot-Tests für alle P0-Antworten und Markdown-Sicherheitsfälle.

### Phase 5: Personen und Mensa

- HKA-Personen-Adapter mit HTML-Fixtures.
- Mensa-GraphQL-Adapter mit Schema-Fixtures.
- Separate Sync-Jobs und Aktualitätsstatus.
- Dozenten- und Mensa-Use-Cases an die Pipeline anschließen.

**Gate:** Parser können bei veränderten oder unvollständigen Antworten
kontrolliert fehlschlagen.

### Phase 6: Personalisierung und komplexe Use-Cases

- Mehrere gespeicherte Kurse.
- Persönlicher Wochenplan.
- Konfliktanalyse als reine Domain-Funktion auf normalisierten Events.
- Hochschulkalender und Campus-Karten.
- Rückfragen für fehlende Kurs- oder Datumsparameter.

**Gate:** Jede Funktion hat einen isolierten Use-Case-Test sowie mindestens
einen Telegram-End-to-End-Test.

### Phase 7: Parallelbetrieb und Ablösung

- Alten und neuen Bot mit getrennten Bot-Tokens oder Test-Chats betreiben.
- Gleiche Szenarien gegen beide Versionen ausführen.
- Unterschiede nicht nur im Text, sondern in Intent, Parametern, Datenstatus
  und Ergebnisanzahl vergleichen.
- Nutzer auf die neue Version umstellen.
- Alte Komponenten erst nach stabiler Betriebsphase entfernen.

**Gate:** Definierte P0-SLOs über mindestens einen vollständigen Wochenzyklus.

---

## 10. Teststrategie

### 10.1 Unit-Tests

- Datums- und Zeitnormalisierung.
- Raum-, Kurs- und Dozentenauflösung.
- iCal- und JSON-Parser.
- HTML-Parser.
- Mensa-Normalisierung.
- Overlap- und Deduplizierungslogik.
- Markdown-Escaping und Telegram-Chunking.

### 10.2 Contract-Tests

Für jede externe Quelle:

- erfolgreiche Antwort;
- leere Antwort;
- 404;
- 429;
- 5xx;
- Timeout;
- Schemaänderung;
- ungültige Pflichtfelder;
- teilweise fehlende Daten.

### 10.3 Pipeline-Tests

Jeder Fall prüft separat:

1. erwarteten Intent;
2. extrahierte Entitäten;
3. gewählten Use-Case;
4. aufgerufene Repository-Methode;
5. typisiertes Ergebnis;
6. gerenderte Antwort.

### 10.4 Telegram-End-to-End

Telegram wird nur für wenige repräsentative Flows eingebunden:

- normale Raumfrage;
- Rückfrage mit fehlendem Datum;
- Kursfrage ohne Treffer;
- Mensa-Menü plus Detailfrage;
- gesperrter Nutzer;
- Rate-Limit;
- Admin-Befehl.

### 10.5 Produktionsnahe Beobachtung

- Erfolgsquote pro Intent.
- Quote von Rückfragen.
- Quelle-Fehler und Parser-Fehler getrennt.
- Cache-Treffer und Cache-Alter.
- Antwortdauer nach Pipeline-Stufe.
- Tool-/Use-Case-Fehler.
- Anzahl „keine Daten“-Antworten.
- Keine vollständigen Nutzernachrichten oder Secrets in Telemetrie.

---

## 11. Datenmigration

Die alte Datenbank wird nicht direkt zum neuen Schema erklärt. Stattdessen:

1. Benutzer, Sperrstatus, Limits und gespeicherte Kurse exportieren.
2. Historien nur migrieren, wenn sie für den neuen Gesprächszustand fachlich
   noch sinnvoll sind.
3. Kurs- und Mensa-Caches verwerfen und neu aufbauen.
4. Dozenten- und Kursindizes als externe Snapshots neu synchronisieren.
5. Migration dry-run ausführen und Anzahl sowie Fehler protokollieren.
6. Erst nach Prüfung den produktiven Import aktivieren.

Runtime-Daten bleiben außerhalb des Git-Diffs.

---

## 12. Abnahmekriterien

Der Neubau ist für den Produktivbetrieb bereit, wenn:

- P0-Szenarien ohne manuelle Sonderlogik funktionieren.
- Keine freie LLM-Antwort als Fakt oder Telegram-Text verwendet wird.
- Jede externe Antwort einen klaren Status und Abrufzeitpunkt besitzt.
- Parser- und Netzwerkfehler sichtbar und reproduzierbar sind.
- Ein fehlerhafter Sync den letzten validierten Snapshot nicht zerstört.
- Keine Anfrage wegen eines unklaren Parameters stillschweigend rät.
- Raum-, Kurs- und Dozentenabfragen mit Fixture-Daten deterministisch testbar
  sind.
- Mensa-Details nur auf Basis bekannter Menü-Daten aufgelöst werden.
- `make lint` sowie die relevanten Tests in CI laufen.
- Ein neuer Agent die Architektur anhand dieses Dokuments und `AGENTS.md`
  nachvollziehen kann.

---

## 13. Empfohlene Reihenfolge für die eigentliche Neucodierung

Nicht mit Telegram-UI, Admin-Kommandos oder weiteren LLM-Prompts beginnen.
Die Reihenfolge sollte sein:

1. Fachliche Verträge und Fixtures.
2. Raumzeit-HTTP- und Parser-Schicht.
3. Normalisierte Domain-Modelle.
4. Raum- und Kurs-Use-Cases.
5. Eine einzige Anfragepipeline.
6. Deterministische Präsentation.
7. Telegram-Anbindung.
8. Personen- und Mensa-Adapter.
9. Personalisierung und Konflikte.
10. Admin, Telemetrie und optionale Komfortfunktionen.

Damit werden die beiden größten Risiken zuerst gelöst: unzuverlässige
Datenbeschaffung und undurchsichtige Anfrageverarbeitung. Alle weiteren
Features werden danach auf dieselben stabilen Verträge aufgesetzt, statt eigene
Sonderpfade zu erzeugen.

---

## 14. Deterministische Kontext-Engine

Der wichtigste Baustein des Neubaus ist eine eigene Kontext-Engine zwischen
Sprachverständnis und Use-Case. Sie erzeugt aus der Nachricht und dem
persistierten Nutzerkontext ein vollständiges, validiertes Request-Modell.

### 14.1 Kontextquellen

Die Engine darf ausschließlich definierte Quellen verwenden:

- aktuelle Nachricht;
- persistierter Nutzerzustand;
- gespeicherte Kurs-Semester;
- kanonischer Raum-, Kurs- und Dozentenkatalog;
- Hochschulkalender;
- lokale Zeitzone und aktuelles Datum;
- validierte Cache-Snapshots;
- explizite Antworten auf vorherige Rückfragen.

Jede verwendete Kontextquelle wird im internen Trace mit Quelle, Version und
Abrufzeit dokumentiert. Das erleichtert Debugging, Regressionstests und die
Erklärung, warum eine Anfrage so beantwortet wurde.

### 14.2 Reihenfolge der Auflösung

1. Explizite Angaben aus der aktuellen Nachricht.
2. Eindeutige Referenzen aus dem offenen Klärungszustand.
3. Eindeutige Nutzerpräferenzen, zum Beispiel gespeicherte Kurse.
4. Kanonische Katalogauflösung.
5. Zentrale Datums- und Zeitlogik.
6. Gültigkeits- und Berechtigungsprüfung.
7. Gezielte Rückfrage bei verbleibender Mehrdeutigkeit.

Das LLM darf diese Reihenfolge nicht überschreiben. Es kann höchstens
alternative Rohbegriffe liefern, die der Resolver prüft.

### 14.3 Beispiel

Bei „Was habe ich morgen?“ wird nicht das LLM gebeten, einen Kurs-Call zu
erzeugen:

```text
LLM: intent=personal_plan, date_expression=morgen
Python: Nutzerprofil laden
Python: gespeicherte Kurs-Keys validieren
Python: morgen in Europe/Berlin berechnen
Python: passende Snapshots/API-Daten abrufen
Python: Events deduplizieren und sortieren
Python: Antwort rendern
```

Fehlt der Kurs im Profil, erzeugt Python die Rückfrage „Welcher Studiengang
und welches Semester soll verwendet werden?“ statt einen Kurs zu erraten.

### 14.4 Determinismus-Tests

Für jeden P0-Use-Case werden folgende Tests verpflichtend:

- gleiche Nachricht + gleicher Kontext + gleicher Snapshot → identisches
  Request-Modell;
- gleiche Eingabe mit veränderter LLM-Rohformulierung → identisches Ergebnis,
  sofern die Entitäten semantisch gleich sind;
- unbekannter Raum/Kurs/Dozent → `not_found`, kein API-Guessing;
- fehlendes Datum → definierte Rückfrage oder dokumentierter Default;
- widersprüchliche Angaben → Rückfrage, kein stilles Überschreiben;
- LLM-Timeout oder ungültiges JSON → kontrollierter Fehlerzustand;
- veralteter Snapshot → sichtbarer Status oder kontrollierter Refresh.
