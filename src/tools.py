"""
Raumzeit API wrapper + Tool-Definitionen im OpenAI-Format (LiteLLM-kompatibel).
Base URL: https://raumzeit.hka-iwi.de
Auth: Bearer JWT via POST /private/api/v1/authentication
"""

import json
import logging
import re
from datetime import date as _date, datetime as _datetime
import httpx
from src.config import settings

log = logging.getLogger(__name__)

_WEEKDAYS = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}


def _parse_timetable_text(text: str, filter_date: str | None = None) -> list[dict]:
    """Parst das Raumzeit-eigene Text-Format: wochentag#start_min#end_min#kurs_id#name"""
    filter_weekday: int | None = None
    if filter_date:
        try:
            d = _date.fromisoformat(filter_date)
            filter_weekday = d.weekday() + 1  # Python 0=Mo → 1=Mo
        except ValueError:
            pass

    bookings = []
    for line in text.strip().split("\n"):
        parts = line.split("#")
        if len(parts) < 5:
            continue
        try:
            day = int(parts[0])
            if filter_weekday is not None and day != filter_weekday:
                continue
            start_min, end_min = int(parts[1]), int(parts[2])
            bookings.append({
                "day": _WEEKDAYS.get(day, str(day)),
                "start": f"{start_min // 60:02d}:{start_min % 60:02d}",
                "end": f"{end_min // 60:02d}:{end_min % 60:02d}",
                "course": parts[3],
                "name": parts[4],
            })
        except (ValueError, IndexError):
            continue
    return bookings

# ---------------------------------------------------------------------------
# Auth & HTTP client
# ---------------------------------------------------------------------------

_token: str | None = None


async def _get_token() -> str:
    global _token
    if _token:
        return _token
    async with httpx.AsyncClient(base_url=settings.raumzeit_base_url) as c:
        r = await c.post(
            "/private/api/v1/authentication",
            json={"login": settings.raumzeit_login, "password": settings.raumzeit_password},
        )
        r.raise_for_status()
        _token = r.json()["accessToken"]
        return _token


def _client(token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.raumzeit_base_url,
        headers={"Authorization": f"Bearer {token}"},
    )


# ---------------------------------------------------------------------------
# Room name cache + fuzzy resolver
# ---------------------------------------------------------------------------

_rooms_cache: list | None = None


def _normalize(name: str) -> str:
    """Entfernt Trennzeichen und lowercased: 'M-105' → 'm105'"""
    return re.sub(r"[\s\-_.]", "", name).lower()


async def _get_rooms_cached() -> list:
    global _rooms_cache
    if _rooms_cache is None:
        token = await _get_token()
        async with _client(token) as c:
            r = await c.get("/api/v1/rooms/all")
            r.raise_for_status()
            _rooms_cache = r.json()
    return _rooms_cache


async def resolve_room_name(query: str) -> str:
    """
    Gibt den kanonischen Raumnamen zurück.
    Sucht zuerst exakt, dann normalisiert (ohne Bindestriche/Leerzeichen).
    Gibt den query unverändert zurück wenn kein Match gefunden.
    """
    rooms = await _get_rooms_cached()

    # Raumnamen aus der API extrahieren (Feld heißt je nach Endpoint 'name' oder 'longName')
    candidates: list[str] = []
    for r in rooms:
        if isinstance(r, dict):
            for field in ("name", "longName", "shortName"):
                if val := r.get(field):
                    candidates.append(str(val))
        elif isinstance(r, str):
            candidates.append(r)

    # 1. Exakter Treffer
    if query in candidates:
        return query

    # 2. Normalisierter Vergleich: 'M-105' == 'M105' == 'm 105'
    q_norm = _normalize(query)
    for candidate in candidates:
        if _normalize(candidate) == q_norm:
            return candidate

    # 3. Kein Treffer → original zurückgeben (API gibt dann selbst Fehler)
    return query


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

async def get_all_rooms() -> list:
    return await _get_rooms_cached()


async def get_room_timetable(room_name: str, date: str | None = None) -> dict:
    canonical = await resolve_room_name(room_name)
    token = await _get_token()
    # Datum-Parameter nur für JSON-Endpoints; Text-Format wird client-seitig gefiltert
    params = {"date": date} if date else {}
    async with _client(token) as c:
        r = await c.get(f"/api/v1/timetables/room/{canonical}", params=params)
        if r.status_code == 404:
            return {"error": f"Raum '{canonical}' nicht gefunden. Bitte prüfe den Raumnamen mit get_all_rooms."}
        r.raise_for_status()

    try:
        entries = r.json()
        bookings = []
        for e in (entries if isinstance(entries, list) else []):
            if not isinstance(e, dict):
                continue
            start = e.get("startTime") or e.get("start", "")
            end   = e.get("endTime")   or e.get("end", "")
            name  = e.get("name") or e.get("longName", "")
            bookings.append({"name": name, "start": start, "end": end})
    except json.JSONDecodeError:
        # API gibt eigenes Text-Format zurück: tag#start_min#end_min#kurs_id#name
        bookings = _parse_timetable_text(r.text, date)
        log.info("Raum '%s': Text-Format, %d Einträge (nach Datumsfilter)", canonical, len(bookings))

    return {
        "room": canonical,
        "queried_date": date or "aktuelle Woche",
        "bookings": bookings,
    }


def _parse_ical(text: str, filter_date: str | None = None) -> list[dict]:
    """Parst iCal-Text und gibt Einträge als Liste von Dicts zurück."""
    events = []
    current: dict = {}
    for line in text.splitlines():
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current:
                events.append(current)
        elif line.startswith("SUMMARY:"):
            current["name"] = line[8:].strip()
        elif line.startswith("DTSTART"):
            val = line.split(":", 1)[-1].strip()
            try:
                dt = _datetime.strptime(val[:15], "%Y%m%dT%H%M%S")
                current["start"] = dt.isoformat()
                current["date"] = dt.date().isoformat()
            except ValueError:
                current["start"] = val
        elif line.startswith("DTEND"):
            val = line.split(":", 1)[-1].strip()
            try:
                dt = _datetime.strptime(val[:15], "%Y%m%dT%H%M%S")
                current["end"] = dt.isoformat()
            except ValueError:
                current["end"] = val
        elif line.startswith("LOCATION:"):
            current["room"] = line[9:].strip()

    if filter_date:
        events = [e for e in events if e.get("date") == filter_date]

    return [{"name": e.get("name",""), "start": e.get("start",""), "end": e.get("end",""), "room": e.get("room","")} for e in events]


async def get_course_timetable(course_semester: str, date: str | None = None) -> dict:
    """
    Format: 'MABB.7' (Kürzel.Semester) oder 'MABB.7.A' (mit Gruppe).
    Nutze get_courses_of_study um das Kürzel zu ermitteln.
    """
    token = await _get_token()
    async with _client(token) as c:
        r = await c.get(
            f"/api/v1/timetables/coursesemester/{course_semester}",
            headers={"Accept": "text/calendar"},
        )
        if r.status_code == 404:
            return {"error": f"Kurs '{course_semester}' nicht gefunden. Format: 'MABB.7' (Kürzel aus get_courses_of_study + Punkt + Semester)."}
        r.raise_for_status()

    bookings = _parse_ical(r.text, date)
    return {"course_semester": course_semester, "queried_date": date or "aktuelles Semester", "bookings": bookings}


async def get_lecturer_timetable(account: str) -> dict:
    token = await _get_token()
    async with _client(token) as c:
        r = await c.get(f"/api/v1/timetables/lecturer/{account}")
        if r.status_code == 404:
            return {"error": f"Dozent '{account}' nicht gefunden. Bitte prüfe das Account-Kürzel."}
        r.raise_for_status()
        entries = r.json()

    bookings = [
        {"name": e.get("name", ""), "start": e.get("startTime", ""), "end": e.get("endTime", "")}
        for e in (entries if isinstance(entries, list) else [])
        if isinstance(e, dict)
    ]
    return {"lecturer": account, "bookings": bookings}


async def get_departments() -> list:
    async with httpx.AsyncClient(base_url=settings.raumzeit_base_url) as c:
        r = await c.get("/api/v1/departments/public")
        r.raise_for_status()
        return r.json()


async def get_courses_of_study(faculty: str | None = None) -> list:
    async with httpx.AsyncClient(base_url=settings.raumzeit_base_url) as c:
        path = f"/api/v1/coursesofstudy/public/{faculty}" if faculty else "/api/v1/coursesofstudy/public"
        r = await c.get(path)
        r.raise_for_status()
    # Komprimieren: nur name und longName — spart ~80% Tokens
    return [{"name": e["name"], "longName": e.get("longName", "")} for e in r.json() if isinstance(e, dict) and "name" in e]


async def get_university_calendar() -> list:
    token = await _get_token()
    async with _client(token) as c:
        r = await c.get("/api/v1/universitycalendar/")
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Tool-Definitionen im OpenAI-Format (LiteLLM-kompatibel)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_all_rooms",
            "description": "Listet alle Räume der Hochschule aus dem Raumzeit-System.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_room_timetable",
            "description": (
                "Zeigt die Belegung eines bestimmten Raums. "
                "Nützlich um zu prüfen, wann ein Raum frei ist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "room_name": {
                        "type": "string",
                        "description": "Raumname wie in Untis, z.B. 'E301' oder 'A104'.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Optionales Datum YYYY-MM-DD. Ohne Angabe = aktuelle Woche.",
                    },
                },
                "required": ["room_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_timetable",
            "description": "Gibt den Stundenplan eines Kurs-Semesters zurück. Format: 'MABB.7' (Kürzel aus get_courses_of_study + Punkt + Semesterzahl). Optionales Datum für Tagesfilter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_semester": {
                        "type": "string",
                        "description": "Kurs-Semester im Format 'KÜRZEL.SEMESTER', z.B. 'MABB.7', 'INFB.3', 'IWIB.5'.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Optionales Datum YYYY-MM-DD zum Filtern auf einen Tag.",
                    },
                },
                "required": ["course_semester"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_lecturer_timetable",
            "description": "Gibt den Stundenplan eines Dozenten anhand seines HKA-Accounts zurück.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account": {
                        "type": "string",
                        "description": "Account/Kürzel des Dozenten, z.B. 'muster'.",
                    },
                },
                "required": ["account"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_departments",
            "description": "Listet alle Departments/Fakultäten der Hochschule.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_courses_of_study",
            "description": "Listet Studiengänge, optional gefiltert nach Fakultät.",
            "parameters": {
                "type": "object",
                "properties": {
                    "faculty": {
                        "type": "string",
                        "description": "Optionaler Fakultätsname zum Filtern.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_university_calendar",
            "description": "Offizielle Uni-Termine: Semesterdaten, Prüfungszeiträume, Ferien.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# ---------------------------------------------------------------------------
# Dispatcher: Tool-Name → async Funktion
# ---------------------------------------------------------------------------

TOOL_HANDLERS = {
    "get_all_rooms":           lambda inp: get_all_rooms(),
    "get_room_timetable":      lambda inp: get_room_timetable(inp["room_name"], inp.get("date")),
    "get_course_timetable":    lambda inp: get_course_timetable(inp["course_semester"], inp.get("date")),
    "get_lecturer_timetable":  lambda inp: get_lecturer_timetable(inp["account"]),
    "get_departments":         lambda inp: get_departments(),
    "get_courses_of_study":    lambda inp: get_courses_of_study(inp.get("faculty")),
    "get_university_calendar": lambda inp: get_university_calendar(),
}
