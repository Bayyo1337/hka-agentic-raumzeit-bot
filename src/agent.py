"""
LLM-Agent: Nutzernachricht → JSON-Extraktion → parallele API-Calls → Formatter.

Das LLM parst nur die Absicht und gibt strukturiertes JSON zurück.
Python führt alle API-Calls aus; formatter.py übernimmt die Antwort.

Unterstützte Provider (per LLM_PROVIDER in .env):
  claude     → Anthropic Claude          (claude-sonnet-4-6)
  gemini     → Google Gemini             (gemini-2.0-flash)
  groq       → Groq / Llama 3.3 70B     (llama-3.3-70b-versatile)
  mistral    → Mistral AI                (mistral-small-latest)
  openrouter → OpenRouter
"""

import asyncio
import json
import logging
import os
from datetime import date
import litellm
from src.config import settings
from src.tools import TOOL_HANDLERS
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

_EXTRACTION_PROMPT_BASE = """Du bist ein Intent-Parser für das Raumzeit-Buchungssystem der HKA (Hochschule Karlsruhe).

Analysiere die Nutzernachricht und gib ausschließlich valides JSON zurück. Kein Text, keine Erklärung.

Verfügbare Tools:
- get_room_timetable: room_name (z.B. "M-001"), date (YYYY-MM-DD, optional)
- get_course_timetable: course_key ("KÜRZEL.SEMESTER", z.B. "MABB.6"), date (YYYY-MM-DD, optional)
- get_lecturer_timetable: account (vollständiger Name z.B. "Masha Taheran", Nachname z.B. "Taheran", oder Kürzel z.B. "tama0001"), date (YYYY-MM-DD, optional)
- get_all_rooms: keine Parameter

Regeln:
- Wochenende → {"weekend": true}
- Konkreter Tag genannt ("Montag", "nächste Woche Dienstag", "heute", "morgen"): GENAU 1 Call mit diesem date
- Ganze Woche ("diese Woche", "nächste Woche" ohne Tagangabe): 5 Calls für Mo–Fr mit je einem date
- Kein Datum ("zeig Stundenplan"): date weglassen
- Max. 6 Calls gesamt

Kürzel-Beispiele: MABB=Maschinenbau, INFB=Informatik, IWIB=Wirtschaftsinformatik, EIMB=Elektro/IT

Ausgabeformat:
{"calls": [{"tool": "TOOLNAME", "args": {"param": "wert"}}, ...]}"""


def _extraction_prompt() -> str:
    return f"{_EXTRACTION_PROMPT_BASE}\n\nHeutiges Datum: {date.today().isoformat()}"


def _resolve_model() -> str:
    if settings.llm_model:
        return settings.llm_model
    provider = _provider_override or settings.llm_provider
    return _DEFAULTS.get(provider, _DEFAULTS["claude"])


def _set_api_key(provider: str | None = None) -> None:
    """Setzt den passenden API-Key als Env-Var für LiteLLM."""
    p = provider or settings.llm_provider
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

_provider_override: str | None = None


def set_provider(provider: str) -> bool:
    """Wechselt den LLM-Provider zur Laufzeit. Gibt False zurück wenn unbekannt."""
    global _provider_override
    if provider not in _DEFAULTS:
        return False
    _provider_override = provider
    _set_api_key(provider)
    return True


def current_provider() -> str:
    return _provider_override or settings.llm_provider


MAX_HISTORY_EXCHANGES = 3  # nur die letzten N Frage+Antwort-Paare behalten
MAX_TOOL_CALLS = 6        # Sicherheitslimit: nie mehr als N API-Calls pro Anfrage


async def run(user_message: str, history: list[dict], user_label: str = "") -> tuple[str, int, int, list]:
    """
    Extraktion: Nutzernachricht → JSON → parallele API-Calls → Formatter → Antwort.

    Returns:
        (reply, input_tokens, output_tokens, collected_results)
    """
    # Wochenend-Schnellcheck: "morgen" auf Sa/So → direkt antworten
    tomorrow = date.today().toordinal() + 1
    tomorrow_weekday = date.fromordinal(tomorrow).weekday()  # 5=Sa, 6=So
    if tomorrow_weekday >= 5 and "morgen" in user_message.lower():
        reply = "Am Wochenende finden keine Vorlesungen statt."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, 0, 0, []

    # History kürzen: lange Antworten (z.B. Raumlisten) kosten viele Tokens
    # und sind für das Intent-Parsing meist irrelevant.
    processed_history = []
    for msg in history:
        content = msg.get("content", "")
        if len(content) > 1000:
            content = content[:1000] + "... [gekürzt]"
        processed_history.append({"role": msg["role"], "content": content})

    model = _resolve_model()
    messages = (
        [{"role": "system", "content": _extraction_prompt()}]
        + processed_history
        + [{"role": "user", "content": user_message}]
    )
    log.debug("User %s: %.80s", user_label, user_message)

    # Einzelner LLM-Call zur Intent-Extraktion
    for attempt in range(3):
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=512,
            )
            break
        except litellm.RateLimitError:
            if attempt == 2:
                raise
            wait = 10 * (attempt + 1)
            log.warning("Rate limit – warte %ds (Versuch %d/3)", wait, attempt + 1)
            await asyncio.sleep(wait)

    usage = getattr(response, "usage", None)
    total_input_tokens = getattr(usage, "prompt_tokens", 0) or 0 if usage else 0
    total_output_tokens = getattr(usage, "completion_tokens", 0) or 0 if usage else 0

    raw = response.choices[0].message.content or ""
    log.debug("LLM Extraktion: %s", raw[:300])

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Ungültiges JSON: %s", raw[:200])
        reply = "Entschuldigung, ich konnte die Anfrage nicht verstehen. Bitte formuliere sie anders."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, total_input_tokens, total_output_tokens, []

    if parsed.get("weekend"):
        reply = "Am Wochenende finden keine Vorlesungen statt."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, total_input_tokens, total_output_tokens, []

    calls = parsed.get("calls", [])[:MAX_TOOL_CALLS]
    if not calls:
        log.warning("Keine Calls im JSON: %s", raw[:200])
        reply = "Entschuldigung, ich konnte die Anfrage nicht verarbeiten."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, total_input_tokens, total_output_tokens, []

    # Alle Calls parallel ausführen
    async def _execute(call: dict) -> tuple[str, dict]:
        name = call.get("tool", "")
        args = call.get("args", {})
        log.debug("LLM → tool: %s(%s)", name, args)
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return name, {"error": f"Unbekanntes Tool: {name}"}
        try:
            return name, await handler(args)
        except Exception as exc:
            log.exception("Tool '%s' fehlgeschlagen", name)
            return name, {"error": str(exc)}

    collected_results: list[tuple[str, dict]] = list(
        await asyncio.gather(*[_execute(c) for c in calls])
    )

    reply = formatter.format_results(collected_results, user_message)
    log.info("Tokens: input=%d output=%d gesamt=%d",
             total_input_tokens, total_output_tokens, total_input_tokens + total_output_tokens)

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    max_entries = MAX_HISTORY_EXCHANGES * 2
    if len(history) > max_entries:
        del history[:-max_entries]

    return reply, total_input_tokens, total_output_tokens, collected_results
