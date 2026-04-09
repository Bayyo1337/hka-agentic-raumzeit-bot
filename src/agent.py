"""
LLM-Agent mit Tool-Use Loop via LiteLLM.
Unterstützte Provider (per LLM_PROVIDER in .env):

  claude   → Anthropic Claude          (claude-sonnet-4-6 / claude-haiku-4-5-20251001)
  gemini   → Google Gemini             (gemini-2.0-flash)  ← kostenlos via AI Studio
  groq     → Groq / Llama 3.3 70B     (llama-3.3-70b-versatile) ← kostenlos
  mistral  → Mistral AI                (mistral-small-latest)    ← kostenlos
  openrouter → OpenRouter (viele Modelle, teils kostenlos)

Modell kann mit LLM_MODEL überschrieben werden.
"""

import asyncio
import json
import logging
import os
from datetime import date
import litellm
from src.config import settings
from src.tools import TOOL_DEFINITIONS, TOOL_HANDLERS

log = logging.getLogger(__name__)
litellm.drop_params = True      # ignoriert unsupported params statt Fehler

# Provider → Standard-Modell
_DEFAULTS: dict[str, str] = {
    "claude":      "claude-sonnet-4-6",
    "gemini":      "gemini/gemini-2.0-flash",
    "groq":        "groq/llama-3.3-70b-versatile",
    "mistral":     "mistral/mistral-small-latest",
    "openrouter":  "openrouter/meta-llama/llama-3.3-70b-instruct:free",
}

_SYSTEM_PROMPT_BASE = """Du bist ein hilfreicher Assistent für das Raumzeit-Buchungssystem der HKA (Hochschule Karlsruhe).
Du hilfst dabei, Räume zu finden, Belegungen zu prüfen und Stundenpläne abzurufen.

WICHTIG – Tool-Nutzung:
- Rufe IMMER die passenden Tools auf, bevor du antwortest. Rate niemals.
- Wenn nach "heute" gefragt wird, nutze das heutige Datum als date-Parameter (YYYY-MM-DD).
- Antworte auf Deutsch, präzise und freundlich."""


def _system_prompt() -> str:
    return f"{_SYSTEM_PROMPT_BASE}\n\nHeutiges Datum: {date.today().isoformat()}"


def _resolve_model() -> str:
    if settings.llm_model:
        return settings.llm_model
    return _DEFAULTS.get(settings.llm_provider, _DEFAULTS["claude"])


def _set_api_key() -> None:
    """Setzt den passenden API-Key als Env-Var für LiteLLM."""
    p = settings.llm_provider
    if p == "claude":
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    elif p == "gemini":
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    elif p == "groq":
        os.environ["GROQ_API_KEY"] = settings.groq_api_key
    elif p == "mistral":
        os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
    elif p == "openrouter":
        os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key


_set_api_key()


MAX_HISTORY_EXCHANGES = 3  # nur die letzten N Frage+Antwort-Paare behalten


async def run(user_message: str, history: list[dict]) -> str:
    """
    Tool-Use Loop: Nutzernachricht → Tool-Calls → finale Antwort.
    Aktualisiert history in-place mit nur User+Assistent-Text (keine Tool-Ergebnisse).

    Args:
        user_message: Aktuelle Nachricht des Nutzers.
        history:      Gesprächsverlauf (wird in-place aktualisiert).

    Returns:
        Finale Textantwort des Assistenten.
    """
    model = _resolve_model()
    # Arbeits-Kopie: enthält Tool-Calls/Ergebnisse, kommt nicht in history
    messages = list(history) + [{"role": "user", "content": user_message}]

    first_call = True
    while True:
        # Ersten Call erzwingen Tools zu nutzen; danach auto (für finale Textantwort)
        tool_choice = "required" if first_call else "auto"
        first_call = False

        for attempt in range(3):
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=[{"role": "system", "content": _system_prompt()}] + messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice=tool_choice,
                    max_tokens=4096,
                )
                break
            except litellm.RateLimitError:
                if attempt == 2:
                    raise
                wait = 10 * (attempt + 1)
                log.warning("Rate limit – warte %ds (Versuch %d/3)", wait, attempt + 1)
                await asyncio.sleep(wait)

        choice = response.choices[0]
        msg = choice.message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            reply = msg.content or ""
            # History in-place aktualisieren: nur User + finale Textantwort
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": reply})
            # Auf MAX_HISTORY_EXCHANGES kürzen (je 2 Einträge pro Exchange)
            max_entries = MAX_HISTORY_EXCHANGES * 2
            if len(history) > max_entries:
                del history[:-max_entries]
            return reply

        # Tool-Calls ausführen
        tool_results = []
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                inp = json.loads(tc.function.arguments)
                handler = TOOL_HANDLERS.get(name)
                result = await handler(inp) if handler else {"error": f"Unbekanntes Tool: {name}"}
            except Exception as exc:
                log.exception("Tool '%s' fehlgeschlagen", name)
                result = {"error": str(exc)}

            content = json.dumps(result, ensure_ascii=False)
            if len(content) > 6000:
                # Kürzen um Token-Limit nicht zu sprengen
                content = content[:6000] + "\n... (gekürzt)"
                log.warning("Tool '%s' Antwort auf 6000 Zeichen gekürzt", name)

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": content,
            })

        messages.extend(tool_results)
