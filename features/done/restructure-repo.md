# Spec: Repository Restructuring for Better Clarity

## Zielsetzung
Das Root-Verzeichnis des Repositorys ist aktuell mit verschiedenen Debug-Skripten, Dokumentationen und Ressourcen überladen. Ziel ist es, eine saubere Struktur zu schaffen, die Core-Logik, Dokumentation, Skripte und Assets strikt trennt.

## Technische Änderungen

### 1. Neue Verzeichnisstruktur
- **`assets/`**: Für statische Ressourcen (PDFs, Bilderquellen).
- **`docs/`**: Für vertiefende Dokumentation (Architektur, Deployments, Changelog).
- **`scripts/debug/`**: Für Einmal-Skripte und Debug-Tools.
- **`scripts/setup/`**: Für Onboarding- und Initialisierungs-Skripte.

### 2. Geplante Verschiebungen
| Quelle | Ziel |
|--------|------|
| `HKA_Lageplan_A4.pdf` | `assets/HKA_Lageplan_A4.pdf` |
| `AGENTS.md` | `docs/AGENTS.md` |
| `CHANGELOG.md` | `docs/CHANGELOG.md` |
| `LIBRARIES.md` | `docs/LIBRARIES.md` |
| `LXC_DEPLOYMENT.md` | `docs/LXC_DEPLOYMENT.md` |
| `debug_db.py` | `scripts/debug/debug_db.py` |
| `debug_db2.py` | `scripts/debug/debug_db2.py` |
| `debug_meals.py` | `scripts/debug/debug_meals.py` |
| `init.sh` | `scripts/setup/init.sh` |
| `fehler-netzwerk?.md` | (Löschen - offensichtliches Artefakt) |

### 3. Code-Anpassungen (Pfad-Updates)
- **`scripts/generate_maps.py`**:
    - Ändere `PDF_PATH = "HKA_Lageplan_A4.pdf"` zu `PDF_PATH = "assets/HKA_Lageplan_A4.pdf"`.
- **`scripts/analyze_map.py`**:
    - Ändere `fitz.open("HKA_Lageplan_A4.pdf")` zu `fitz.open("assets/HKA_Lageplan_A4.pdf")`.
- **`Makefile`**:
    - Da die Skripte in Unterordner verschoben werden, müssen Aufrufe wie `uv run python scripts/check.py` geprüft werden. (Falls `check.py` im Root von `scripts/` bleibt, ist keine Änderung nötig).
    - `init.sh` Aufruf (falls vorhanden) anpassen.

## Datenmodell
Keine Änderungen an der Datenbank.

## Test-Strategie
1. **Lauffähigkeit prüfen**: `make run` muss erfolgreich starten (prüft Imports und Grundkonfiguration).
2. **Karten-Generierung prüfen**: `uv run python scripts/generate_maps.py` ausführen, um sicherzustellen, dass die PDF in `assets/` gefunden wird.
3. **E2E-Tests**: `make test-e2e-dynamic` ausführen.
