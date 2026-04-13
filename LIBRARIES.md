# Verwendete Bibliotheken – Lizenzen und Nutzerrechte

Dieses Dokument listet alle direkten Abhängigkeiten des Projekts `raumzeit-ki-agent` auf, jeweils mit exakter Version (Stand: `uv.lock`), Lizenztyp und einer Zusammenfassung der wesentlichen Nutzerrechte. Die Zusammenfassungen sind eigenständig formuliert und stellen keine Rechtsgutachten dar.

---

## Produktivabhängigkeiten

### 1. anthropic `0.92.0`
- **Herausgeber:** Anthropic, PBC
- **Lizenz:** MIT License
- **Nutzerrechte:** Freie Nutzung, Weitergabe und Modifikation – auch in proprietären Produkten – solange der Lizenzhinweis erhalten bleibt. Keine Copyleft-Pflicht.
- **Quelle:** https://github.com/anthropics/anthropic-sdk-python

---

### 2. litellm `1.83.4`
- **Herausgeber:** BerriAI
- **Lizenz:** MIT License
- **Nutzerrechte:** Wie bei MIT: volle Freiheit zur privaten und kommerziellen Nutzung, Änderung und Verteilung. Einzige Auflage: Lizenz- und Copyright-Vermerk bleiben erhalten.
- **Quelle:** https://github.com/BerriAI/litellm

---

### 3. python-telegram-bot `22.7`
- **Herausgeber:** python-telegram-bot contributors
- **Lizenz:** GNU Lesser General Public License v3 (LGPL-3.0)
- **Nutzerrechte:** Die Bibliothek darf in eigene (auch proprietäre) Anwendungen eingebunden werden, ohne dass der eigene Quellcode offengelegt werden muss. Werden jedoch die Bibliothek selbst modifiziert und weitergegeben, müssen die Änderungen unter LGPL-3.0 veröffentlicht werden.
- **Quelle:** https://github.com/python-telegram-bot/python-telegram-bot

---

### 4. httpx `0.28.1`
- **Herausgeber:** Encode OSS Ltd.
- **Lizenz:** BSD 3-Clause License
- **Nutzerrechte:** Sehr permissiv: Nutzung, Modifikation und Weitergabe in Quellcode- und Binärform erlaubt – auch kommerziell. Drei Bedingungen: Urheberrechtshinweis beibehalten, Lizenztext in Binärverteilungen beilegen, Name des Rechteinhabers nicht für Werbezwecke verwenden.
- **Quelle:** https://github.com/encode/httpx

---

### 5. pydantic-settings `2.13.1`
- **Herausgeber:** Samuel Colvin u. a.
- **Lizenz:** MIT License
- **Nutzerrechte:** Uneingeschränkte Nutzung und Weitergabe unter Beibehaltung des Lizenzhinweises.
- **Quelle:** https://github.com/pydantic/pydantic-settings

---

### 6. python-dotenv `1.0.1`
- **Herausgeber:** Saurabh Kumar
- **Lizenz:** BSD 3-Clause License
- **Nutzerrechte:** Identisch mit httpx (siehe oben): permissive Nutzung unter Beibehaltung der drei Auflagen (Copyright-Vermerk, Lizenzdatei, kein Namens-Missbrauch).
- **Quelle:** https://github.com/theskumar/python-dotenv

---

### 7. aiosqlite `0.22.1`
- **Herausgeber:** John Reese / Facebook, Inc.
- **Lizenz:** MIT License
- **Nutzerrechte:** Freie Nutzung auch kommerziell; Lizenzhinweis muss erhalten bleiben.
- **Quelle:** https://github.com/omnilib/aiosqlite

---

### 8. httpcore `1.0.9`
- **Herausgeber:** Encode OSS Ltd.
- **Lizenz:** BSD 3-Clause License
- **Nutzerrechte:** Wie httpx (gleicher Herausgeber, gleiche Lizenzbedingungen).
- **Quelle:** https://github.com/encode/httpcore

---

### 9. rich `14.3.3`
- **Herausgeber:** Will McGugan
- **Lizenz:** MIT License
- **Nutzerrechte:** Volle Nutzungs- und Weitergabefreiheit unter Beibehaltung des Lizenz- und Copyright-Textes.
- **Quelle:** https://github.com/Textualize/rich

---

### 10. pymupdf `1.27.2.2`
- **Herausgeber:** Artifex Software Inc.
- **Lizenz:** GNU Affero General Public License v3 (AGPL-3.0) **oder** kommerzielle Lizenz
- **Nutzerrechte (AGPL-3.0):** Starke Copyleft-Lizenz. Wer ein Programm, das PyMuPDF einbindet, über ein Netzwerk bereitstellt (SaaS, Webanwendung) oder weitergibt, ist verpflichtet, den **vollständigen Quellcode** der eigenen Anwendung unter AGPL-3.0 zu veröffentlichen. Für proprietäre oder kommerzielle Nutzung ohne Offenlegung ist eine kostenpflichtige Lizenz von Artifex erforderlich.
- **Hinweis für dieses Projekt:** Solange der Bot nicht öffentlich vertrieben oder als Netzwerkdienst angeboten wird, ist die Nutzung unter AGPL-3.0 intern möglich. Bei einer öffentlichen Bereitstellung (z. B. als Telegram-Bot für Dritte) muss der Quellcode des Bots unter AGPL-3.0 offengelegt werden.
- **Quelle:** https://github.com/pymupdf/PyMuPDF

---

### 11. pillow `12.2.0`
- **Herausgeber:** Jeffrey A. Clark (Alex) und die Pillow-Community (Ursprung: PIL von Fredrik Lundh)
- **Lizenz:** HPND – Historical Permission Notice and Disclaimer (PIL-Lizenz)
- **Nutzerrechte:** Äußerst permissiv. Nutzung, Kopie, Modifikation und Weitergabe – auch kommerziell – ohne Einschränkung; einzige Pflicht ist die Beibehaltung des Urheberrechtshinweises und des Haftungsausschlusses.
- **Quelle:** https://github.com/python-pillow/Pillow

---

## Entwicklungsabhängigkeiten (dev-only, nicht im Produktivbetrieb)

### 12. pytest `9.0.3`
- **Herausgeber:** Holger Krekel u. a.
- **Lizenz:** MIT License
- **Nutzerrechte:** Freie Nutzung; wird nur lokal zum Testen ausgeführt, ist nicht im ausgelieferten Produkt enthalten.
- **Quelle:** https://github.com/pytest-dev/pytest

---

### 13. pytest-asyncio `1.3.0`
- **Herausgeber:** Tin Tvrtkovic u. a.
- **Lizenz:** Apache License 2.0
- **Nutzerrechte:** Permissiv: kommerzielle Nutzung, Modifikation und Weitergabe erlaubt. Ein Hinweis auf vorgenommene Änderungen ist erforderlich; der Lizenztext muss beiliegen. Keine Copyleft-Pflicht.
- **Quelle:** https://github.com/pytest-dev/pytest-asyncio

---

### 14. ruff `0.15.10`
- **Herausgeber:** Astral Software Inc.
- **Lizenz:** MIT License
- **Nutzerrechte:** Freie Nutzung als Linter/Formatter; nicht im ausgelieferten Produkt enthalten.
- **Quelle:** https://github.com/astral-sh/ruff

---

## Build-System

### 15. hatchling (Build-Backend)
- **Herausgeber:** Ofek Lev
- **Lizenz:** MIT License
- **Nutzerrechte:** Wird ausschließlich zum Bauen des Pakets verwendet; nicht im Laufzeit-Produkt enthalten.
- **Quelle:** https://github.com/pypa/hatch

---

## Lizenz-Kurzübersicht

| # | Paket | Version | Lizenz | Copyleft? |
|---|-------|---------|--------|-----------|
| 1 | anthropic | 0.92.0 | MIT | Nein |
| 2 | litellm | 1.83.4 | MIT | Nein |
| 3 | python-telegram-bot | 22.7 | LGPL-3.0 | Schwach (nur Bibliothek selbst) |
| 4 | httpx | 0.28.1 | BSD-3-Clause | Nein |
| 5 | pydantic-settings | 2.13.1 | MIT | Nein |
| 6 | python-dotenv | 1.0.1 | BSD-3-Clause | Nein |
| 7 | aiosqlite | 0.22.1 | MIT | Nein |
| 8 | httpcore | 1.0.9 | BSD-3-Clause | Nein |
| 9 | rich | 14.3.3 | MIT | Nein |
| 10 | **pymupdf** | 1.27.2.2 | **AGPL-3.0** | **Ja – stark (inkl. Netzwerknutzung)** |
| 11 | pillow | 12.2.0 | HPND | Nein |
| 12 | pytest *(dev)* | 9.0.3 | MIT | Nein |
| 13 | pytest-asyncio *(dev)* | 1.3.0 | Apache-2.0 | Nein |
| 14 | ruff *(dev)* | 0.15.10 | MIT | Nein |
| 15 | hatchling *(build)* | — | MIT | Nein |

---

## Wichtigster Hinweis: PyMuPDF / AGPL-3.0

Die Abhängigkeit `pymupdf` unterliegt der AGPL-3.0 – der restriktivsten Lizenz im Projekt.
Da der Telegram-Bot für externe Nutzer betrieben wird (Netzwerkdienst), **greift die AGPL-3.0-Netzwerkklausel**: der gesamte Quellcode des Bots muss bei öffentlicher Bereitstellung unter AGPL-3.0 lizenziert und zugänglich gemacht werden. Wird eine Veröffentlichung des Quellcodes vermieden, ist eine kommerzielle Lizenz von Artifex Software erforderlich.

---

*Dokument erstellt auf Basis von `pyproject.toml` und `uv.lock`. Alle Lizenzangaben beziehen sich auf die jeweils angegebene Version. Dieses Dokument wurde eigenständig verfasst; es wurden keine Texte aus bestehenden Lizenzübersichten oder Projektdokumentationen übernommen.*
