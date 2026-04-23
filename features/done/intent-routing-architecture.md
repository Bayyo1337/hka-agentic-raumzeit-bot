
    Zielbild und Intent-Taxonomie festlegen

    Definiere feste Intent-Klassen passend zu den vorhandenen Tools: room_timetable, course_timetable, lecturer_timetable, lecturer_info, mensa_menu, mensa_details, campus_map, university_calendar, conflict_analysis, smalltalk/fallback.
    Lege pro Intent fest, welche Tools erlaubt sind und welche Pflicht-Parameter benötigt werden.

    Router-Schicht als eigene Komponente einführen

    Neues zentrales Routing-Modul (z. B. src/router.py) zwischen bot.py und agent.py planen.
    Output des Routers standardisieren: intent, confidence, entities, route_strategy (direkt/fallback/ask-clarification).

    Zweistufige Intent-Classification aufbauen

    Stufe 1: schnelle, deterministische Vor-Klassifikation (Keywords, Muster wie Raumformat, Kurskey, Dozenten-Kürzel, Mensa-Begriffe, Lageplan-Begriffe).
    Stufe 2: LLM-basierte Klassifikation nur bei niedriger Sicherheit oder Mehrdeutigkeit.

    Agent-Flows nach Intent trennen

    agent.py von „ein Prompt für alles“ auf intent-spezifische Extraktionspfade umstellen.
    Pro Intent nur relevante Tool-Optionen erlauben, damit weniger Fehlrouten und weniger Tokens entstehen.
    Bestehende Sonderlogik (z. B. Kurs-Eskalation in bot.py) als eigener Route-Pfad explizit anbinden.

    Integration in bot.py definieren

    In handle_message zuerst Router ausführen, danach je nach Route:
        direkter Tool-Call/Flow bei hoher Sicherheit
        intent-spezifischer Agent-Call
        Rückfrage an Nutzer bei Ambiguität (statt blindem Tool-Aufruf).

    Konfigurierbarkeit und Rollout absichern

    Feature-Flag in config.py/state.py für schrittweise Aktivierung (router_enabled, optional router_strict_mode).
    Fallback auf bisherigen agent.run-Pfad, falls Router fehlschlägt.

    Beobachtbarkeit ergänzen

    Intent-, Confidence- und Fallback-Quote im Logging erfassen (src.bot/src.agent).
    Optional in SQLite (db) einfache Metriken speichern, um Fehlklassifikationen messbar zu machen.

    Qualitätssicherung planen

    Unit-Tests für Klassifikation (typische deutsche User-Queries inkl. Tippfehler/Mehrdeutigkeiten).
    End-to-End-Tests für kritische Flows: Raum frei, persönlicher Plan, Mensa, Lageplan, Konfliktanalyse, Eskalationsdialog.
    Akzeptanzkriterien: weniger falsche Tools, stabilere Antworten, geringere Tokenkosten gegenüber aktuellem Stand.
