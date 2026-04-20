# Spec: Dekodierung von Allergenen und Zusatzstoffen

## Zielsetzung
Aktuell liefert die Mensa-API Allergene und Zusatzstoffe als rohe Kürzel (z. B. `FI`, `ML`, `COLORANT`). Das LLM gibt diese Kürzel dann meist unübersetzt an den Nutzer weiter ("Allergene: FI, ML"), was für Endnutzer schwer verständlich ist.
Das Ziel ist es, diese Kürzel direkt im Backend automatisch in lesbare Klartext-Begriffe (z. B. `Fisch`, `Milch`, `Farbstoff`) zu übersetzen, bevor sie an das LLM zurückgegeben und in der Datenbank gecacht werden.

## Technische Änderungen

### 1. `src/tools.py`
- **Konstanten einführen**: Erstelle zwei Dictionaries `_ALLERGEN_MAP` und `_ADDITIVE_MAP` im Mensa-Integrationsbereich der Datei.
  - *Beispiele Allergene*: `{"WE": "Weizen", "RO": "Roggen", "DI": "Dinkel", "EI": "Ei", "FI": "Fisch", "ER": "Erdnüsse", "SO": "Soja", "ML": "Milch", "SL": "Sellerie", "SN": "Senf", "SE": "Sesam", "SU": "Schwefeldioxid/Sulfite", "LU": "Lupinen", "WT": "Weichtiere", "HN": "Haselnüsse", "MA": "Mandeln", "WA": "Walnüsse", "KA": "Kaschunüsse", "PE": "Pekannüsse", "PA": "Paranüsse", "PI": "Pistazien", "QD": "Queenslandnüsse"}`
  - *Beispiele Zusatzstoffe*: `{"COLORANT": "Farbstoff", "PRESERVING_AGENTS": "Konservierungsstoff", "ANTIOXIDANT_AGENTS": "Antioxidationsmittel", "FLAVOR_ENHANCER": "Geschmacksverstärker", "PHOSPHATE": "Phosphat", "SULFUR_DIOXIDE": "Geschwefelt", "BLACKENED": "Geschwärzt", "SURFACE_WAXED": "Gewachst", "SWEETENER": "Süßungsmittel", "PHENYLALANINE": "Enthält eine Phenylalaninquelle", "TAURINE": "Taurin", "NITRITE_PICKLING_SALT": "Nitritpökelsalz", "CAFFEINE": "Koffeinhaltig", "QUININE": "Chininhaltig", "ALCOHOL": "Alkohol"}`
  - *(Hinweis: Offizielle Mappings der API sollten so weit wie möglich abgedeckt werden. Unbekannte Kürzel bleiben als Fallback erhalten).*

- **Dekodierungs-Logik in `get_mensa_menu`**:
  - Innerhalb der API-Verarbeitungsschleife (`for m in line.get("meals", []):`) müssen die Listen für Allergene und Zusatzstoffe modifiziert werden.
  - Iteriere über `m.get("allergens", [])` und ersetze jedes Element durch den gemappten String aus `_ALLERGEN_MAP` (oder behalte das Kürzel, falls nicht im Mapping gefunden).
  - Wiederhole dies für `m.get("additives", [])` mit `_ADDITIVE_MAP`.
  - Da dieser Eingriff *vor* dem Einfügen in den `_MEALS_CACHE` und dem Aufruf von `db.save_mensa_meals` geschieht, greifen die übersetzten Namen automatisch in allen nachgelagerten Caches und Detail-Abfragen (`get_mensa_meal_details`).

## Datenmodell
Es sind keine Änderungen an der Datenbank-Struktur (`src/db.py`) notwendig. Da in der Tabelle `mensa_meals` JSON persistiert wird, landen die bereits dekodierten Arrays zukünftig automatisch als Klartext in der SQLite-Datenbank. (Hinweis: Bereits gecachte Daten vom aktuellen Tag in der Datenbank werden bei der nächsten Ausführung von `get_mensa_menu` überschrieben).

## Test-Strategie
1. Erstellung eines Test-Skripts `scripts/test_mensa_decoding.py`, welches `get_mensa_menu` aufruft.
2. Das Skript überprüft bei einem Gericht, ob die Liste der Allergene Wörter (z.B. "Weizen", "Milch") statt reiner Buchstabencodes (z.B. "WE", "ML") enthält.
3. Danach wird `get_mensa_meal_details` für dasselbe Gericht aufgerufen, um zu bestätigen, dass auch der Einzel-Lookup von den dekodierten Arrays profitiert.

## Lösung & Abschluss
Die Dekodierung wurde erfolgreich in `src/tools.py` implementiert. Es wurden zwei Mapping-Dictionaries (`_ALLERGEN_MAP` und `_ADDITIVE_MAP`) erstellt, die die rohen API-Kürzel (z.B. `WE`, `COLORANT`) in lesbare Klartext-Begriffe (z.B. `Weizen`, `Farbstoff`) übersetzen. Die Übersetzung findet direkt bei der Menü-Abfrage in `get_mensa_menu` statt, sodass auch alle nachgelagerten Caches davon profitieren. Verifiziert durch Echtdaten-Tests.
