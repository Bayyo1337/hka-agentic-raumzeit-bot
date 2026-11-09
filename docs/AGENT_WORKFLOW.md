# Agentischer Entwicklungsworkflow

## Ziel

Die Entwicklung wird in klar getrennte Rollen aufgeteilt. Jede Rolle kann mit
einem eigenen OpenAI-Modell laufen, ohne dass Modellnamen oder Zugangsdaten in
Produktionscode gelangen.

Die Zuordnung steht in `.agents/models.toml`.

## Rollen und Modellwahl

| Rolle | Aufgabe | Standardmodell |
|---|---|---|
| Strategist | Umfang, Reihenfolge und Abnahmekriterien | `gpt-4.1` |
| Researcher | Codeanalyse und Reproduktion | `gpt-4.1-mini` |
| Implementer | Umsetzung und fokussierte Tests | `gpt-4.1` |
| Reviewer | unabhängige Fehler- und Regressionssuche | `o3` |
| Integrator | Review-Fixes und Abschlussprüfung | `gpt-4.1` |

Die Modelle sind bewusst nicht alle gleich:

- Recherche ist häufig mechanisch und kann kostengünstiger laufen.
- Implementierung und Planung benötigen mehr Kontext und Schlussfolgerung.
- Review profitiert von einer unabhängigen, reasoning-starken Perspektive.

## Ausführung

Ein OpenAI-kompatibler Runner sollte für jeden Lauf:

1. das Rollenprofil aus `.agents/models.toml` laden;
2. `AGENT_<ROLE>_MODEL` als optionalen Override prüfen;
3. den effektiven Provider und das Modell im Handoff dokumentieren;
4. nur das für die Rolle notwendige Repository-Rechteprofil verwenden;
5. nach jedem Gate den Lauf stoppen oder an die nächste Rolle übergeben.

Das konfigurierte Modell lässt sich prüfen mit:

```bash
python scripts/resolve_agent_model.py strategist
python scripts/resolve_agent_model.py researcher
AGENT_REVIEWER_MODEL=o3 python scripts/resolve_agent_model.py reviewer
```

Die Datei löst nur die Modellwahl auf. Der eigentliche Runner setzt
`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, Timeouts und Limits außerhalb des
Repositories.

## Verbindliche Übergaben

Jede Übergabe nutzt `.agents/templates/handoff.md` und enthält:

- Ziel und Abnahmekriterien;
- betroffene Dateien und konkrete Codebelege;
- effektives Modell und mögliche Fallbacks;
- Reproduktion bzw. Baseline;
- Validierungsbefehle und deren Ergebnis;
- offene Risiken und den nächsten Verantwortlichen.

Ein Agent darf nicht einfach „fertig“ melden, wenn ein Gate fehlt. Ein
fehlgeschlagener Test, ein unklarer Scope oder ein nicht reproduzierbarer Fehler
führt zurück an die zuständige Rolle.

## Parallelisierung

Parallel gearbeitet wird nur bei disjunkten Dateimengen, zum Beispiel:

- Researcher analysiert `src/tools.py`;
- ein anderer Researcher analysiert ausschließlich Fixtures;
- danach implementiert genau ein Implementer die freigegebenen Dateien.

Strategist, Implementer und Integrator dürfen nicht gleichzeitig dieselben
Dateien bearbeiten. Das verhindert widersprüchliche Änderungen und macht
Reviews nachvollziehbar.

## Eskalation

Ein stärkeres Modell wird nur bei einem konkreten Grund aktiviert:

- unklarer oder widersprüchlicher Scope;
- fehlende Akzeptanzkriterien;
- Testfehler nach einer Änderung;
- widersprüchliche Änderungen;
- schwerer Review-Fund;
- fehlende oder nicht reproduzierbare Validierung.

Das Ziel ist nicht, jede Aufgabe mit dem teuersten Modell zu lösen, sondern
Kosten und Qualität anhand der tatsächlichen Schwierigkeit zu steuern.

## Sicherheitsregeln

- Keine API-Schlüssel, Tokens oder `.env`-Inhalte in Handoffs.
- Keine vollständigen geheimen Prompts oder externen Nutzerdaten in Logs.
- Modellnamen dürfen versioniert werden; Zugangsdaten nicht.
- Der Integrator prüft vor Abschluss, dass keine Runtime-Daten oder Secrets
  im Diff enthalten sind.

## Abgrenzung zum alten Gemini-Workflow

`.gemini/` bleibt als Gemini-CLI-spezifische Kompatibilitätsschicht erhalten.
Der rollenbasierte Workflow unter `.agents/` ist die gemeinsame, bevorzugte
Definition. Ein neuer OpenAI-Runner sollte `.agents/models.toml`,
`.agents/roles/` und das Handoff-Template verwenden, statt den alten
Gemini-Strategist direkt zu kopieren.
