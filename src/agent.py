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

_SYSTEM_PROMPT_BASE = """Du bist ein Assistent für das Raumzeit-Buchungssystem der HKA (Hochschule Karlsruhe).

REGEL: Du MUSST bei JEDER Anfrage zuerst ein Tool aufrufen. Antworte NIE ohne vorherigen Tool-Aufruf.
- Raumfragen → get_room_timetable (bei Unklarheit erst get_all_rooms)
- Kurs-Stundenplan → IMMER zuerst get_courses_of_study aufrufen um den exakten Bezeichner zu finden, dann get_course_timetable
- Dozenten-Stundenplan → get_lecturer_timetable (Account-Kürzel, z.B. "muel")
- "heute" = heutiges Datum, "morgen" = heutiges Datum + 1 Tag (YYYY-MM-DD)

ANTWORT-FORMAT (Telegram Markdown):
- Telegram Markdown: *fett* mit einfachen Sternchen (NICHT **doppelt**)
- Nutze Emojis sparsam aber gezielt: 📅 für Datum, 🏫 für Raum, ✅ für frei, 🔴 für belegt
- Belegungen als kompakte Liste: `09:50–11:20 Werkstoffkunde`
- Freie Slots klar hervorheben, sinnvolle Uhrzeiten nennen (nicht "ab 00:00")
- Kein Smalltalk am Ende, keine Rückfragen
- Antworte auf Deutsch, präzise und knapp"""


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


async def run(user_message: str, history: list[dict]) -> tuple[str, int, int]:
    """
    Tool-Use Loop: Nutzernachricht → Tool-Calls → finale Antwort.
    Aktualisiert history in-place mit nur User+Assistent-Text (keine Tool-Ergebnisse).

    Returns:
        (reply, input_tokens, output_tokens)
    """
    model = _resolve_model()
    messages = list(history) + [{"role": "user", "content": user_message}]

    any_tool_called = False
    no_tool_retries = 0
    total_input_tokens = 0
    total_output_tokens = 0
    while True:
        # Tools erzwingen, bis mindestens ein Tool-Call stattgefunden hat.
        # Danach "auto", damit das Modell die finale Textantwort geben kann.
        tool_choice = "auto" if any_tool_called else "required"

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

        usage = getattr(response, "usage", None)
        if usage:
            total_input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            total_output_tokens += getattr(usage, "completion_tokens", 0) or 0

        choice = response.choices[0]
        msg = choice.message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            if not any_tool_called and no_tool_retries < 2:
                # Modell hat tool_choice="required" ignoriert — explizit nachfordern
                no_tool_retries += 1
                log.warning("Modell hat Tools nicht aufgerufen (Versuch %d/2) – fordere erneut", no_tool_retries)
                messages.append({
                    "role": "user",
                    "content": "Bitte nutze die verfügbaren Tools, um die Anfrage zu beantworten. Antworte nicht ohne Tool-Aufruf.",
                })
                continue

            if not msg.content and any_tool_called and no_tool_retries < 2:
                # Modell hat Tool-Ergebnisse bekommen aber nichts geantwortet — nachfordern
                no_tool_retries += 1
                log.warning("Modell hat nach Tool-Calls leere Antwort gegeben – fordere Interpretation")
                messages.append({
                    "role": "user",
                    "content": "Bitte beantworte jetzt die ursprüngliche Frage auf Basis der Tool-Ergebnisse.",
                })
                continue

            reply = msg.content or "Ich konnte keine Antwort generieren. Bitte versuche es nochmal."
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": reply})
            max_entries = MAX_HISTORY_EXCHANGES * 2
            if len(history) > max_entries:
                del history[:-max_entries]
            log.info("Tokens: input=%d output=%d gesamt=%d", total_input_tokens, total_output_tokens, total_input_tokens + total_output_tokens)
            return reply, total_input_tokens, total_output_tokens

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

        any_tool_called = True
        messages.extend(tool_results)
