# Automatisierte End-to-End (E2E) Test-Framework

## Problemstellung
Mit dem neuen Intent-Routing und den dynamischen Agent-Flows reicht manuelles Testen im Terminal oder Telegram nicht mehr aus, um Regressionen zu erkennen. Unit-Tests sind gut für kleine Module (wie Regex im Router), testen aber nicht das LLM-Verhalten, die Integration der Tools und den finalen Formatter-Output.

## Idee
Wir benötigen eine automatisierte E2E-Testschicht:
1.  **Testfälle (Fixtures)**: Eine JSON/YAML Datei mit 10-20 typischen Nutzerfragen (inkl. Tippfehlern). Pro Frage definieren wir:
    *   `expected_intent`: Welcher Intent muss greifen?
    *   `expected_tools`: Welche API-Tools *müssen* vom Agenten aufgerufen werden?
    *   `expected_keywords`: Welche Strings (z.B. "Euro", "Uhr", "Raum") müssen im erzeugten Markdown-Text auftauchen?
2.  **Headless Runner (`pytest` oder Skript)**: Ein Skript, das diese Fragen durch `bot.handle_message` oder `agent.run` jagt (ohne Telegram) und die Outputs validiert. Das Skript muss mit `make test-e2e` startbar sein.
3.  **Skill Integration**: Der `qa-reviewer` Skill soll diese Tests vor einem Commit ausführen, um sicherzustellen, dass keine Kern-Features kaputt gegangen sind.
4.  **Mocking vs. Real**: Für den Anfang machen wir *echte* LLM-Calls (kein LLM-Mocking), um auch Prompt-Regressionen abzufangen. API-Calls zur HKA können echt bleiben, da sie Lese-Operationen sind.

Ziel ist es, dass man mit einem einzigen Befehl den kompletten Bot auf "Verständnis" und "Antwortqualität" prüfen kann.