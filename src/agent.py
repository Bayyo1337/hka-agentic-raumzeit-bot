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
from src import formatter

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
- Kurs-Stundenplan → get_course_timetable direkt mit Format "KÜRZEL.SEMESTER" (z.B. "MABB.6")
  → get_courses_of_study NUR aufrufen wenn das Kürzel wirklich unklar ist
  → Kürzel-Beispiele: MABB=Maschinenbau Bachelor, INFB=Informatik Bachelor, IWIB=Wirtschaftsinformatik
- Dozenten-Stundenplan → get_lecturer_timetable (Account-Kürzel, z.B. "muel")
- "heute" = heutiges Datum, "morgen" = heutiges Datum + 1 Tag (YYYY-MM-DD)
- Samstag und Sonntag: KEIN Tool-Call nötig – antworte direkt "Am Wochenende finden keine Vorlesungen statt"
- "diese Woche" / "nächste Tage": MAXIMAL 5 separate Datums-Calls (Mo–Fr)
- Ohne konkretes Datum ("zeig Stundenplan"): KEIN date-Parameter – gibt aktuelle Woche zurück
- NIEMALS mehr als 6 Tool-Calls pro Anfrage

WICHTIG: Deine Aufgabe ist NUR die Tool-Auswahl und Parametrisierung.
Die Formatierung der Antwort übernimmt das System automatisch.
Gib nach den Tool-Calls KEINEN Text aus."""


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
MAX_TOOL_CALLS = 6        # Sicherheitslimit: nie mehr als N Tool-Calls pro Anfrage


async def run(user_message: str, history: list[dict], user_label: str = "") -> tuple[str, int, int, list]:
    """
    Tool-Use Loop: Nutzernachricht → Tool-Calls → Python-Formatter → Antwort.
    Das LLM wählt nur Tools aus; die Antwortgenerierung übernimmt formatter.py.

    Returns:
        (reply, input_tokens, output_tokens, collected_results)
    """
    # Wochenend-Schnellcheck: "morgen" auf Sa/So → direkt antworten
    tomorrow = date.today().toordinal() + 1
    tomorrow_weekday = date.fromordinal(tomorrow).weekday()  # 5=Sa, 6=So
    msg_lower = user_message.lower()
    if tomorrow_weekday >= 5 and "morgen" in msg_lower:
        reply = "Am Wochenende finden keine Vorlesungen statt."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, 0, 0, []

    model = _resolve_model()
    messages = list(history) + [{"role": "user", "content": user_message}]
    log.debug("User %s: %.80s", user_label, user_message)

    collected_results: list[tuple[str, dict]] = []
    total_tool_calls = 0
    no_tool_retries = 0
    total_input_tokens = 0
    total_output_tokens = 0

    while True:
        # Solange Tools aufgerufen wurden oder noch kein einziger Call stattfand:
        # tool_choice="required" erzwingt Tool-Call.
        # Nach mindestens einem Call: "auto" erlaubt dem Modell zu stoppen.
        tool_choice = "auto" if collected_results else "required"

        for attempt in range(3):
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=[{"role": "system", "content": _system_prompt()}] + messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice=tool_choice,
                    max_tokens=512,  # nur Tool-Calls nötig, kein langer Text
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

        if msg.tool_calls:
            for tc in msg.tool_calls:
                log.debug("LLM → tool: %s(%s)", tc.function.name, tc.function.arguments)
        else:
            log.debug("LLM → fertig (keine weiteren Tool-Calls)")

        if not msg.tool_calls:
            if not collected_results and no_tool_retries < 2:
                # Modell hat tool_choice="required" ignoriert — explizit nachfordern
                no_tool_retries += 1
                log.warning("Modell hat Tools nicht aufgerufen (Versuch %d/2)", no_tool_retries)
                messages.append({
                    "role": "user",
                    "content": "Bitte nutze die verfügbaren Tools, um die Anfrage zu beantworten.",
                })
                continue

            # Alle Tool-Calls abgeschlossen → Python-Formatter übernimmt
            reply = formatter.format_results(collected_results, user_message)
            log.info("Tokens: input=%d output=%d gesamt=%d", total_input_tokens, total_output_tokens, total_input_tokens + total_output_tokens)

            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": reply})
            max_entries = MAX_HISTORY_EXCHANGES * 2
            if len(history) > max_entries:
                del history[:-max_entries]

            return reply, total_input_tokens, total_output_tokens, collected_results

        # Sicherheitslimit prüfen
        total_tool_calls += len(msg.tool_calls)
        if total_tool_calls > MAX_TOOL_CALLS:
            log.warning("Tool-Call-Limit (%d) erreicht – formatiere bisherige Ergebnisse", MAX_TOOL_CALLS)
            reply = formatter.format_results(collected_results, user_message)
            log.info("Tokens: input=%d output=%d gesamt=%d", total_input_tokens, total_output_tokens, total_input_tokens + total_output_tokens)
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": reply})
            if len(history) > MAX_HISTORY_EXCHANGES * 2:
                del history[:-MAX_HISTORY_EXCHANGES * 2]
            return reply, total_input_tokens, total_output_tokens, collected_results

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

            collected_results.append((name, result))

            content = json.dumps(result, ensure_ascii=False)
            if len(content) > 6000:
                content = content[:6000] + "\n... (gekürzt)"
                log.warning("Tool '%s' Antwort auf 6000 Zeichen gekürzt", name)

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": content,
            })

        messages.extend(tool_results)
