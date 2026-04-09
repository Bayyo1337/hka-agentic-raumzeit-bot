"""
Claude agent mit Tool-Use Loop.
Empfängt Nutzernachrichten, ruft Raumzeit-Tools auf, gibt finale Antwort zurück.
"""

import json
import logging
from anthropic import AsyncAnthropic
from src.config import settings
from src.tools import TOOL_DEFINITIONS, TOOL_HANDLERS

log = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """Du bist ein hilfreicher Assistent für das Raumzeit-Buchungssystem.
Du hilfst Nutzerinnen und Nutzern dabei, Räume zu finden, Verfügbarkeiten zu prüfen
und Buchungen zu erstellen. Antworte immer auf Deutsch, präzise und freundlich."""


async def run(user_message: str, history: list[dict] | None = None) -> str:
    """
    Führt den Tool-Use Loop durch und gibt die finale Textantwort zurück.

    Args:
        user_message: Aktuelle Nachricht des Nutzers.
        history:      Bisherige Gesprächshistorie (Liste von Anthropic-Message-Dicts).

    Returns:
        Finale Textantwort des Assistenten.
    """
    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    while True:
        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Assistenten-Turn zur History hinzufügen
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Reine Textantwort extrahieren
            return next(
                (block.text for block in response.content if hasattr(block, "text")),
                "",
            )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                handler = TOOL_HANDLERS.get(block.name)
                if handler is None:
                    result = {"error": f"Unbekanntes Tool: {block.name}"}
                else:
                    try:
                        result = await handler(block.input)
                    except Exception as exc:
                        log.exception("Tool '%s' fehlgeschlagen", block.name)
                        result = {"error": str(exc)}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        # Unerwarteter stop_reason
        log.warning("Unerwarteter stop_reason: %s", response.stop_reason)
        break

    return "Es ist ein unerwarteter Fehler aufgetreten."
