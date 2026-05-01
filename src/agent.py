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
import re
from datetime import date, timedelta
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
    "next_occurrence": {
        "tools": ["get_next_occurrence"],
        "instruction": "Du bist Spezialist für die Suche nach dem nächsten Termin eines Moduls. Extrahiere den Modulnamen (z.B. 'Mathe 1') und optional den Kurs-Key."
    },
    "conflict_analysis": {
        "tools": ["find_timetable_conflicts"],
        "instruction": "Du bist Spezialist für Überschneidungen im Stundenplan. Extrahiere Kurs (z.B. 'Maschinenbau'), base_sem und target_sem. Der module_filter ist OPTIONAL. Wenn kein Modul genannt wurde, lasse ihn leer und vergleiche die gesamten Semester. Frage NIEMALS nach Modulen!"
    },
    "smalltalk_fallback": {
        "tools": [
            "get_room_timetable", "get_course_timetable", "get_lecturer_timetable", 
            "get_lecturer_info", "get_mensa_menu", "get_mensa_meal_details", "get_all_rooms", 
            "get_departments", "get_courses_of_study", "get_university_calendar", 
            "find_timetable_conflicts", "get_campus_map", "get_next_occurrence"
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
    "university_calendar": "get_university_calendar: keine Parameter",
    "find_timetable_conflicts": "find_timetable_conflicts: course (z.B. \"Maschinenbau\"), base_sem (int, Semester in dem das Fach liegt), target_sem (int, Semester mit dem verglichen werden soll), module_filter (optional, z.B. \"etechnik\")",
    "get_next_occurrence": "get_next_occurrence: module_name (z.B. \"Mathe 1\"), course_key (optional, z.B. \"MABB.2\") - NUTZE DIES BEI FRAGEN WIE 'Wann habe ich...?'",
    "get_campus_map": "get_campus_map: room_or_building (z.B. \"LI-145\" oder \"Gebäude M\") - NUTZE DIES NUR BEI FRAGEN NACH DEM ORT/STOCKWERK!"
}


def resolve_german_weekday(text: str, ref_date: date) -> date | None:
    """Extrahiert einen deutschen Wochentag aus Text und gibt das nächste Datum ab ref_date zurück."""
    weekdays = {
        "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3,
        "freitag": 4, "samstag": 5, "sonntag": 6
    }
    text_lower = text.lower()
    for name, day_idx in weekdays.items():
        if name in text_lower:
            days_ahead = day_idx - ref_date.weekday()
            if days_ahead < 0:
                days_ahead += 7
            return ref_date + timedelta(days=days_ahead)
    return None


def filter_history_by_intent(history: list[dict], intent: str) -> list[dict]:
    timetable_keywords = ["raum", "kurs", "dozent", "stundenplan", "plan", "m-102", "thermodynamik", "vorlesung"]
    mensa_keywords = ["mensa", "speiseplan", "essen", "hunger", "allergene", "gericht", "schnitzel", "wahlessen"]
    
    filtered = []
    if intent in ["mensa_menu", "mensa_details"]:
        for msg in history:
            content_lower = msg["content"].lower()
            if not any(kw in content_lower for kw in timetable_keywords):
                filtered.append(msg)
    elif intent in ["course_timetable", "room_timetable", "lecturer_timetable", "next_occurrence"]:
        for msg in history:
            content_lower = msg["content"].lower()
            if not any(kw in content_lower for kw in mensa_keywords):
                filtered.append(msg)
    else:
        filtered = history
        
    return filtered


def _extraction_prompt(primary_course: Optional[str] = None, intent: str = "smalltalk_fallback") -> str:
    config = INTENT_CONFIGS.get(intent, INTENT_CONFIGS["smalltalk_fallback"])
    instruction = config["instruction"]
    allowed_tools = config["tools"]
    
    tools_str = "\n".join(f"- {ALL_TOOLS_DEF[t]}" for t in allowed_tools if t in ALL_TOOLS_DEF)
    
    # 1. Basis-Instruktion
    sections = [
        instruction,
        "\nAnalysiere die Nutzernachricht und gib ausschließlich valides JSON zurück. Kein Text, keine Erklärung.",
        "\nVerfügbare Tools:\n" + tools_str
    ]

    # 2. Zeit-Regeln (nur wenn Tools Datumsangaben benötigen oder für Konsistenz)
    time_intents = ["room_timetable", "course_timetable", "lecturer_timetable", "mensa_menu", "lecturer_info", "smalltalk_fallback"]
    if intent in time_intents:
        sections.append("""
Regeln zur Zeitrechnung:
- Konkreter Tag genannt: GENAU 1 Call mit diesem date (YYYY-MM-DD)
- "nächste Woche" ohne Tag → alle 5 Tage (Mo–Fr) der nächsten Kalenderwoche
- "die nächsten Tage" / "diese Woche" → alle verbleibenden Tage der aktuellen Woche
- Datum in der Vergangenheit → meist Tippfehler, prüfe Folgemonat/-jahr
- Max. 6 Calls gesamt""")

    # 3. Fehler-Handling & Priorisierung
    if intent in ["course_timetable", "smalltalk_fallback", "next_occurrence"]:
        sections.append(f"""
Fehler-Handling & Priorisierung:
1. PERSÖNLICHE ANFRAGE: Wenn der Nutzer nach SEINEM Plan fragt ("mein Plan", "was habe ich heute"), MUSST du die Kurse aus dem 'Nutzer-Profil' ({primary_course}) verwenden. Erzeuge für JEDEN Kurs einen `get_course_timetable` Call.
2. WANN HABE ICH X: Wenn der Nutzer fragt "Wann habe ich <Modul>?", nutze IMMER `get_next_occurrence`. Wenn ein Profil vorhanden ist ({primary_course}), nutze die Kurse daraus als `course_key`.
3. EXPLIZITE ANFRAGE: Wenn der Nutzer einen konkreten Kurs-Key nennt (z.B. "MABB.2", "Maschinenbau Sem 3"), ignoriere das Profil und führe den Call nur für diesen Key aus.
4. KEIN PROFIL: Wenn es eine persönliche Anfrage ist, aber das Profil 'Kein Kurs hinterlegt' zeigt, gib {{"error": "no_course"}} zurück.""")

    # 4. Format & Kontext
    sections.append("""
Kürzel-Beispiele: MABB=Maschinenbau, INFB=Informatik, IWIB=Wirtschaftsinformatik, EIMB=Elektro/IT

Ausgabeformat:
{"calls": [{"tool": "TOOLNAME", "args": {"param": "wert"}}, ...]}""")

    # 5. Aktuelle Wochentage zur Orientierung
    today = date.today()
    days_info = []
    for i in range(7):
        d = today + timedelta(days=i)
        days_info.append(f"{d.strftime('%A')}: {d.isoformat()}")
    sections.append("\nAktuelle Wochentage:\n" + "\n".join(days_info))

    prompt = "\n".join(sections)
    profile_info = f"\nNutzer-Profil: Der Nutzer studiert '{primary_course}'." if primary_course else "\nNutzer-Profil: Kein Kurs hinterlegt."
    
    return f"{prompt}\n\nHeutiges Datum: {date.today().isoformat()}{profile_info}"

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

def redact_pii(text: str) -> str:
    """Best-effort Redaktion von sensiblen Daten (Emails, Telefonnummern, IBANs)."""
    if not text: return text
    # 1. IBAN (zuerst, da sie Zahlen enthält die als Telefonnummer missverstanden werden könnten)
    # Deckt gängige EU-IBANs ab (Ländercode + Prüfziffer + bis zu 30 Stellen)
    text = re.sub(r'\b[A-Z]{2}\d{2}[ \d]{12,30}\b', '[IBAN]', text)
    
    # 2. Email
    text = re.sub(r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b', '[EMAIL]', text)
    
    # 3. Telefon (mind. 7 Ziffern, um nicht versehentlich Jahreszahlen oder IDs zu treffen)
    # Erkennt Formate wie +49 123..., 0123-456..., 0721 1234567
    text = re.sub(r'(\+?\d[\d\s-]{5,}\d)', lambda m: '[PHONE]' if sum(c.isdigit() for c in m.group(0)) >= 7 else m.group(0), text)
    
    return text

MAX_HISTORY_EXCHANGES = 3
MAX_TOOL_CALLS = 6

async def run(user_message: str, history: list[dict], user_id: int | None = None, user_label: str = "", primary_course: str | None = None, intent: str = "smalltalk_fallback") -> tuple[str, int, int, list]:
    # 1. Privacy Settings laden
    from src import db
    privacy = {"allow_history": 1, "allow_llm": 1}
    if user_id:
        privacy = await db.get_privacy_settings(user_id)

    # Redaktion auf User-Input
    safe_message = redact_pii(user_message)

    if not privacy.get("allow_llm", True):
        return "❌ <b>KI-Verarbeitung deaktiviert.</b>\n\nDu hast die KI-Verarbeitung in deinen /consent Einstellungen deaktiviert. Bitte aktiviere sie, um natürliche Anfragen zu stellen.", 0, 0, []

    # Nutzer-Profil laden (immer aktuell aus DB, um History-Verwirrung zu vermeiden)
    if user_id:
        u = await db.get_user(user_id)
        if u:
            config = await db.get_user_course_config(user_id)
            if config:
                keys = [c["key"] for c in config]
                primary_course = f"[{', '.join(keys)}]"
            else:
                primary_course = u.get("primary_course")

    # Historie filtern & redigieren (falls erlaubt)
    if privacy.get("allow_history", True):
        filtered_history = filter_history_by_intent(history, intent)
    else:
        filtered_history = []

    processed_history = []
    for msg in filtered_history:
        content = redact_pii(msg.get("content", ""))
        if len(content) > 1000: content = content[:1000] + "... [gekürzt]"
        processed_history.append({"role": msg["role"], "content": content})

    model = _resolve_model()
    # System Prompt mit aktuellem Profil
    sys_prompt = _extraction_prompt(primary_course, intent)
    messages = [{"role": "system", "content": sys_prompt}]
    
    if processed_history:
        messages.extend(processed_history)
        # Kontext-Reminder direkt vor der User-Nachricht
        ctx = primary_course or "Kein Kurs hinterlegt"
        user_content = f"[Nutzer-Profil: {ctx}] {safe_message}"
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": safe_message})

    # Hardened Logging
    log.info("LLM Request for %s (Intent: %s)", user_label or f"User:{user_id}", intent)
    if settings.debug and os.environ.get("ALLOW_PII_DEBUG_LOGS") == "1":
        log.debug("FULL PROMPT (PII ENABLED):\n%s", json.dumps(messages, indent=2, ensure_ascii=False))
    else:
        log.debug("FULL PROMPT (PII REDACTED):\n%s", json.dumps(messages, indent=2, ensure_ascii=False).replace(user_message, "[USER_MSG_REDACTED]"))
    
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

    # Deterministic Weekday Override
    for call in calls:
        if call.get("tool") in ["get_mensa_menu", "get_mensa_meal_details"]:
            resolved_date = resolve_german_weekday(user_message, date.today())
            if resolved_date:
                if "args" not in call: call["args"] = {}
                call["args"]["date"] = resolved_date.isoformat()
                log.debug("Override date to %s due to weekday in message", resolved_date.isoformat())

    async def _execute(call: dict) -> tuple[str, dict]:
        name = call.get("tool", "")
        args = call.get("args", {})
        if user_id:
            args["user_id"] = user_id
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

    reply = formatter.format_results(collected_results, safe_message)
    
    if privacy.get("allow_history", True):
        history.append({"role": "user", "content": safe_message})
        history.append({"role": "assistant", "content": reply})
        max_entries = MAX_HISTORY_EXCHANGES * 2
        if len(history) > max_entries:
            del history[:-max_entries]

    log.info("Tokens: input=%d output=%d gesamt=%d",
             total_input_tokens, total_output_tokens, total_input_tokens + total_output_tokens)

    return reply, total_input_tokens, total_output_tokens, collected_results
