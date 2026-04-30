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
from typing import Optional
import litellm
from src.config import settings
from src.tools import TOOL_HANDLERS
from src import formatter

log = logging.getLogger(__name__)
litellm.drop_params = True

_DEFAULTS: dict[str, str] = {
    "claude":      "claude-sonnet-4-6",
    "gemini":      "gemini/gemini-2.0-flash",
    "groq":        "groq/llama-3.3-70b-versatile",
    "mistral":     "mistral/mistral-small-latest",
    "openrouter":  "openrouter/meta-llama/llama-3.3-70b-instruct:free",
}

# Mapping of Intent to allowed tools and specific prompt instructions
INTENT_CONFIGS = {
    "room_timetable": {
        "tools": ["get_room_timetable", "get_all_rooms"],
        "instruction": "Du bist Spezialist für Raum-Stundenpläne. Extrahiere den Raumnamen (z.B. 'M-102') und das Datum."
    },
    "course_timetable": {
        "tools": ["get_course_timetable", "get_courses_of_study"],
        "instruction": "Du bist Spezialist für Studiengangs-Stundenpläne. Extrahiere den Kurs-Key ('KÜRZEL.SEMESTER', z.B. 'MABB.6') und das Datum."
    },
    "lecturer_timetable": {
        "tools": ["get_lecturer_timetable"],
        "instruction": "Du bist Spezialist für Dozenten-Stundenpläne. Extrahiere den Dozenten-Namen oder das Kürzel und das Datum."
    },
    "lecturer_info": {
        "tools": ["get_lecturer_info"],
        "instruction": "Du bist Spezialist für Dozenten-Infos (E-Mail, Sprechzeiten). Extrahiere den Dozenten-Namen oder das Kürzel."
    },
    "mensa_menu": {
        "tools": ["get_mensa_menu"],
        "instruction": "Du bist Mensa-Spezialist. Extrahiere Canteen (z.B. 'Moltke') und Datum."
    },
    "mensa_details": {
        "tools": ["get_mensa_meal_details"],
        "instruction": "Du bist Mensa-Spezialist für Detailinfos (Allergene, Preise). Extrahiere die meal_id."
    },
    "campus_map": {
        "tools": ["get_campus_map"],
        "instruction": "Du bist Spezialist für Lagepläne und Wegbeschreibungen auf dem Campus. Extrahiere den gesuchten Raum oder das Gebäude."
    },
    "university_calendar": {
        "tools": ["get_university_calendar"],
        "instruction": "Du bist Spezialist für Semesterzeiten und Feiertage. Keine Parameter nötig."
    },
    "conflict_analysis": {
        "tools": ["find_timetable_conflicts"],
        "instruction": "Du bist Spezialist für Überschneidungen im Stundenplan. Extrahiere Kurs (z.B. 'Maschinenbau'), base_sem, target_sem und ggf. module_filter."
    },
    "smalltalk_fallback": {
        "tools": [
            "get_room_timetable", "get_course_timetable", "get_lecturer_timetable", 
            "get_lecturer_info", "get_mensa_menu", "get_mensa_meal_details", "get_all_rooms", 
            "get_departments", "get_courses_of_study", "get_university_calendar", 
            "find_timetable_conflicts", "get_campus_map"
        ],
        "instruction": "Du bist ein allgemeiner Intent-Parser für das Raumzeit-Buchungssystem der HKA. Wähle das passende Tool aus."
    }
}

ALL_TOOLS_DEF = {
    "get_room_timetable": "get_room_timetable: room_name (z.B. \"M-102\"), date (YYYY-MM-DD, optional)",
    "get_course_timetable": "get_course_timetable: course_key (\"KÜRZEL.SEMESTER\", z.B. \"MABB.6\"), date (YYYY-MM-DD, optional)",
    "get_lecturer_timetable": "get_lecturer_timetable: account (vollständiger Name z.B. \"Masha Taheran\", Nachname z.B. \"Taheran\", oder Kürzel z.B. \"tama0001\"), date (YYYY-MM-DD, optional)",
    "get_lecturer_info": "get_lecturer_info: account (Name oder Kürzel) - NUTZE DIES NUR FÜR KONTAKTINFOS (E-Mail, Sprechzeit).",
    "get_mensa_menu": "get_mensa_menu: canteen (Name z.B. \"Moltke\", \"Adenauerring\", optional), date (YYYY-MM-DD, optional). Default Canteen ist \"Moltke\".",
    "get_mensa_meal_details": "get_mensa_meal_details: meal_id (technische ID aus get_mensa_menu)",
    "get_all_rooms": "get_all_rooms: keine Parameter",
    "get_departments": "get_departments: keine Parameter",
    "get_courses_of_study": "get_courses_of_study: faculty_id (optional)",
    "get_university_calendar": "get_university_calendar: keine Parameter",
    "find_timetable_conflicts": "find_timetable_conflicts: course (z.B. \"Maschinenbau\"), base_sem (int, Semester in dem das Fach liegt), target_sem (int, Semester mit dem verglichen werden soll), module_filter (optional, z.B. \"etechnik\")",
    "get_campus_map": "get_campus_map: room_or_building (z.B. \"LI-145\" oder \"Gebäude M\") - NUTZE DIES NUR BEI FRAGEN NACH DEM ORT/STOCKWERK!"
}

def _extraction_prompt(primary_course: Optional[str] = None, intent: str = "smalltalk_fallback") -> str:
    config = INTENT_CONFIGS.get(intent, INTENT_CONFIGS["smalltalk_fallback"])
    instruction = config["instruction"]
    allowed_tools = config["tools"]
    
    tools_str = "\n".join(f"- {ALL_TOOLS_DEF[t]}" for t in allowed_tools if t in ALL_TOOLS_DEF)
    
    base = f"""{instruction}

Analysiere die Nutzernachricht und gib ausschließlich valides JSON zurück. Kein Text, keine Erklärung.

Verfügbare Tools:
{tools_str}

Regeln:
- Konkreter Tag genannt ("Montag", "nächste Woche Dienstag", "heute", "morgen"): GENAU 1 Call mit diesem date
- Ganze Woche ("diese Woche", "nächste Woche" ohne Tagangabe): 5 Calls für Mo–Fr mit je einem date
- Kein Datum ("zeig Stundenplan"): date weglassen
- Max. 6 Calls gesamt

Regeln zur Zeitrechnung:
- "nächste Woche" ohne Tag → alle 5 Tage (Mo–Fr) der nächsten Kalenderwoche.
- "die nächsten Tage" / "diese Woche" → alle verbleibenden Tage der aktuellen Woche (inkl. Wochenende).
- "und sonst?" / "was noch?" → restliche Termine der aktuellen Woche.
- Datum am Wochenende (Sa/So) → Normaler Call mit diesem date (API liefert auch Blockveranstaltungen).
- Datum in der Vergangenheit → meist Tippfehler, prüfe ob der gleiche Tag im nächsten Monat/Jahr gemeint sein könnte.

Fehler-Handling:
- Wenn der Nutzer explizit nach SEINEM persönlichen Plan fragt ("mein Plan", "was habe ich heute"), aber im 'Nutzer-Profil' unten steht 'Kein Kurs hinterlegt', darfst du keinen Kurs raten! Gib in diesem Fall exakt {{"error": "no_course"}} zurück.
- WICHTIG: Wenn der Nutzer explizite Kurs-Keys (z.B. MABB, INFB) oder Semester in der Nachricht nennt, ist dies KEINE persönliche Plan-Anfrage. In diesem Fall musst du die Tools (find_timetable_conflicts, get_course_timetable) ganz normal mit den extrahierten Daten aufrufen!


Kürzel-Beispiele: MABB=Maschinenbau, INFB=Informatik, IWIB=Wirtschaftsinformatik, EIMB=Elektro/IT

Ausgabeformat:
{{"calls": [{{"tool": "TOOLNAME", "args": {{"param": "wert"}}}}, ...]}}"""
    
    profile_info = f"\nNutzer-Profil: Der Nutzer studiert '{primary_course}'." if primary_course else "\nNutzer-Profil: Kein Kurs hinterlegt."
    return f"{base}\n\nHeutiges Datum: {date.today().isoformat()}{profile_info}"

def _resolve_model() -> str:
    if settings.llm_model:
        return settings.llm_model
    provider = _provider_override or settings.llm_provider
    return _DEFAULTS.get(provider, _DEFAULTS["claude"])

def _set_api_key(provider: str | None = None) -> None:
    p = provider or settings.llm_provider
    if p == "claude": os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    elif p == "gemini": os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    elif p == "groq": os.environ["GROQ_API_KEY"] = settings.groq_api_key
    elif p == "mistral": os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
    elif p == "openrouter": os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

_set_api_key()
_provider_override: str | None = None

def set_provider(provider: str) -> bool:
    global _provider_override
    if provider not in _DEFAULTS: return False
    _provider_override = provider
    _set_api_key(provider)
    return True

def current_provider() -> str:
    return _provider_override or settings.llm_provider

MAX_HISTORY_EXCHANGES = 3
MAX_TOOL_CALLS = 6

async def run(user_message: str, history: list[dict], user_label: str = "", primary_course: str | None = None, intent: str = "smalltalk_fallback") -> tuple[str, int, int, list]:
    processed_history = []
    for msg in history:
        content = msg.get("content", "")
        if len(content) > 1000: content = content[:1000] + "... [gekürzt]"
        processed_history.append({"role": msg["role"], "content": content})

    model = _resolve_model()
    messages = (
        [{"role": "system", "content": _extraction_prompt(primary_course, intent)}]
        + processed_history
        + [{"role": "user", "content": user_message}]
    )
    log.debug("User %s (Intent: %s): %.80s", user_label, intent, user_message)
    log.debug("LLM Provider: %s | Model: %s", settings.llm_provider, model)
    log.debug("Vollständiger Prompt für LLM:\n%s", json.dumps(messages, indent=2, ensure_ascii=False))
    
    _set_api_key()

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
            if attempt == 2: raise
            wait = 10 * (attempt + 1)
            await asyncio.sleep(wait)

    usage = getattr(response, "usage", None)
    total_input_tokens = getattr(usage, "prompt_tokens", 0) or 0 if usage else 0
    total_output_tokens = getattr(usage, "completion_tokens", 0) or 0 if usage else 0

    raw = response.choices[0].message.content or ""
    log.debug("LLM Extraktion: %s", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        reply = "Entschuldigung, ich konnte die Anfrage nicht verstehen. Bitte formuliere sie anders."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, total_input_tokens, total_output_tokens, []

    if parsed.get("error") == "no_course":
        reply = "Bitte nutze /setcourse, um deinen Studiengang zu hinterlegen, damit ich dir deinen persönlichen Plan zeigen kann."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, total_input_tokens, total_output_tokens, []

    calls = parsed.get("calls", [])[:MAX_TOOL_CALLS]
    if not calls:
        reply = "Entschuldigung, ich konnte die Anfrage nicht verarbeiten."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply, total_input_tokens, total_output_tokens, []

    async def _execute(call: dict) -> tuple[str, dict]:
        name = call.get("tool", "")
        args = call.get("args", {})
        handler = TOOL_HANDLERS.get(name)
        if not handler: return name, {"error": f"Unbekanntes Tool: {name}"}
        try:
            res = await handler(args)
            return name, res
        except Exception as exc:
            return name, {"error": f"Interner Fehler im Tool {name}: {exc}"}

    collected_results: list[tuple[str, dict]] = list(
        await asyncio.gather(*[_execute(c) for c in calls])
    )

    reply = formatter.format_results(collected_results, user_message)
    
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    max_entries = MAX_HISTORY_EXCHANGES * 2
    if len(history) > max_entries:
        del history[:-max_entries]

    log.info("Tokens: input=%d output=%d gesamt=%d",
             total_input_tokens, total_output_tokens, total_input_tokens + total_output_tokens)

    return reply, total_input_tokens, total_output_tokens, collected_results
