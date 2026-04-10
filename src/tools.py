"""
Raumzeit API wrapper + Tool-Definitionen im OpenAI-Format (LiteLLM-kompatibel).
Base URL: https://raumzeit.hka-iwi.de
Auth: Bearer JWT via POST /private/api/v1/authentication
"""

import asyncio
import json
import logging
import re
from datetime import date as _date, datetime as _datetime
import httpx
from src.config import settings
from src import db

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
        log.debug("API → GET /timetables/room/%s  params=%s", canonical, params)
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
        log.debug("API ← %d  (%d Belegungen, JSON)", r.status_code, len(bookings))
    except json.JSONDecodeError:
        bookings = _parse_timetable_text(r.text, date)
        log.debug("API ← %d  (%d Belegungen, Text-Format)", r.status_code, len(bookings))

    return {
        "room": canonical,
        "queried_date": date or "aktuelle Woche",
        "bookings": bookings,
    }


def _current_week_range() -> tuple[str, str]:
    """Gibt Mo–Fr der aktuellen Woche als ISO-Strings zurück."""
    today = _date.today()
    monday = today - __import__("datetime").timedelta(days=today.weekday())
    friday = monday + __import__("datetime").timedelta(days=4)
    return monday.isoformat(), friday.isoformat()


def _parse_ical(text: str, filter_date: str | None = None,
                date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    """Parst iCal-Text und gibt Einträge als Liste von Dicts zurück.
    filter_date: exakter Tagesfilter
    date_from/date_to: Datumsbereich (inklusiv)
    """
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
            val = line.split(":", 1)[-1].strip().rstrip("Z")
            # TZID-Format: "Europe/Berlin:20260410T113000" → letztes Segment nach ":"
            if ":" in val:
                val = val.split(":")[-1].rstrip("Z")
            try:
                dt = _datetime.strptime(val[:15], "%Y%m%dT%H%M%S")
                current["start"] = dt.isoformat()
                current["date"] = dt.date().isoformat()
            except ValueError:
                current["start"] = val
        elif line.startswith("DTEND"):
            val = line.split(":", 1)[-1].strip().rstrip("Z")
            if ":" in val:
                val = val.split(":")[-1].rstrip("Z")
            try:
                dt = _datetime.strptime(val[:15], "%Y%m%dT%H%M%S")
                current["end"] = dt.isoformat()
            except ValueError:
                current["end"] = val
        elif line.startswith("LOCATION:"):
            current["room"] = line[9:].strip()

    if filter_date:
        events = [e for e in events if e.get("date") == filter_date]
    elif date_from and date_to:
        events = [e for e in events if date_from <= e.get("date", "") <= date_to]

    return [{"name": e.get("name",""), "start": e.get("start",""), "end": e.get("end",""), "room": e.get("room","")} for e in events]


async def _fetch_ical(course_semester: str, date: str | None = None,
                      date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    """Hilfsfunktion: iCal für einen course_semester-Key abrufen und parsen."""
    token = await _get_token()
    async with _client(token) as c:
        log.debug("API → GET /timetables/coursesemester/%s", course_semester)
        r = await c.get(
            f"/api/v1/timetables/coursesemester/{course_semester}",
            headers={"Accept": "text/calendar"},
        )
        if r.status_code == 404:
            return []
        r.raise_for_status()
    bookings = _parse_ical(r.text, date, date_from=date_from, date_to=date_to)
    log.debug("API ← %d  (%d Einträge, iCal) [%s]", r.status_code, len(bookings), course_semester)
    return bookings


async def get_course_timetable(course_semester: str, date: str | None = None) -> dict:
    """
    Format: 'MABB.7' (Kürzel.Semester) oder 'MABB.7.A' (mit Gruppe).
    Ohne Datum: aktuelle Woche (Mo–Fr). Mit Datum: nur dieser Tag.
    Wenn der Index bekannt ist, werden alle Gruppen automatisch kombiniert.
    """
    parts = course_semester.split(".")
    if len(parts) == 2:
        variants = await db.get_course_variants(parts[0], int(parts[1]))
        if not variants:
            variants = [course_semester]
    else:
        variants = [course_semester]

    # Ohne Datum → aktuelle Woche
    if date:
        fetch_kwargs = {"date": date}
        label = date
    else:
        week_from, week_to = _current_week_range()
        fetch_kwargs = {"date_from": week_from, "date_to": week_to}
        label = f"KW {_date.today().isocalendar()[1]} ({week_from} – {week_to})"

    results = await asyncio.gather(*[_fetch_ical(key, **fetch_kwargs) for key in variants])
    all_bookings = []
    for key, bookings in zip(variants, results):
        for b in bookings:
            b["gruppe"] = key
        all_bookings.extend(bookings)

    return {
        "course_semester": course_semester,
        "queried_date": label,
        "bookings": all_bookings,
    }


async def get_lecturer_timetable(account: str) -> dict:
    token = await _get_token()
    async with _client(token) as c:
        log.debug("API → GET /timetables/lecturer/%s", account)
        r = await c.get(f"/api/v1/timetables/lecturer/{account}")
        log.debug("API ← %d  (%d bytes)", r.status_code, len(r.text))
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


async def build_course_index() -> int:
    """
    Entdeckt alle gültigen course_semester-Kombinationen (MABB.7, MABB.7.A, ...) per API-Probing.
    Läuft vollständig parallel, kein Rate-Limiting nötig.
    Gibt die Anzahl gefundener Einträge zurück.
    """
    log.info("Kurs-Index: Aufbau gestartet...")
    courses = await get_courses_of_study()
    abbreviations = [c["name"] for c in courses if c.get("name")]
    log.info("Kurs-Index: %d Studiengänge gefunden", len(abbreviations))

    # Phase 1: Für alle Kürzel alle Semester 1–10 parallel prüfen
    sem_tasks = [
        (abbr, sem, _probe_course_key(f"{abbr}.{sem}"))
        for abbr in abbreviations
        for sem in range(1, 11)
    ]
    sem_results = await asyncio.gather(*[t for _, _, t in sem_tasks])

    valid_base: list[tuple[str, int]] = []  # (abbreviation, semester)
    for (abbr, sem, _), ok in zip(sem_tasks, sem_results):
        if ok:
            valid_base.append((abbr, sem))

    log.info("Kurs-Index: %d gültige Semester-Kombinationen", len(valid_base))

    # Phase 2: Für alle gültigen Semester Gruppen prüfen.
    # Bekannte Einzelbuchstaben aus API-Analyse über alle Fakultäten: A,B,C,D,F,K,P,S,U,Z,E
    # + mehrstellige Kürzel die in der Praxis vorkommen
    _single = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    _multi = ["DF", "AB", "AF", "BF", "KP", "KU", "PU", "U1", "U2", "U61", "U62", "U63"]
    group_suffixes = _single + _multi

    grp_tasks = [
        (abbr, sem, suffix, _probe_course_key(f"{abbr}.{sem}.{suffix}"))
        for abbr, sem in valid_base
        for suffix in group_suffixes
    ]
    grp_results = await asyncio.gather(*[t for _, _, _, t in grp_tasks])

    # Ergebnisse sammeln
    entries: list[dict] = []
    # Basis-Keys immer aufnehmen
    for abbr, sem in valid_base:
        entries.append({"full_key": f"{abbr}.{sem}", "abbreviation": abbr, "semester": sem, "group_letter": ""})
    # Gruppen-Keys nur wenn 200
    for (abbr, sem, suffix, _), ok in zip(grp_tasks, grp_results):
        if ok:
            entries.append({"full_key": f"{abbr}.{sem}.{suffix}", "abbreviation": abbr, "semester": sem, "group_letter": suffix})

    await db.save_course_index(entries)
    log.info("Kurs-Index: %d Einträge gespeichert", len(entries))
    return len(entries)


async def fetch_course_brute_force(course_semester: str, date: str | None = None) -> dict:
    """
    Ignoriert den Index – probt alle bekannten Suffixe direkt für diesen Kurs.
    Aktualisiert den Index mit neu entdeckten Varianten.
    """
    parts = course_semester.split(".")
    abbr, sem = parts[0], parts[1]
    base_key = f"{abbr}.{sem}"
    all_suffixes = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + [
        "DF", "AB", "AF", "BF", "KP", "KU", "PU", "U1", "U2", "U61", "U62", "U63"
    ]
    probe_results = await asyncio.gather(*[_probe_course_key(f"{base_key}.{s}") for s in all_suffixes])
    valid_variants = [base_key] + [f"{base_key}.{s}" for s, ok in zip(all_suffixes, probe_results) if ok]

    if date:
        fetch_kwargs = {"date": date}
    else:
        week_from, week_to = _current_week_range()
        fetch_kwargs = {"date_from": week_from, "date_to": week_to}

    fetch_results = await asyncio.gather(*[_fetch_ical(key, **fetch_kwargs) for key in valid_variants])
    all_bookings = []
    for key, bookings in zip(valid_variants, fetch_results):
        for b in bookings:
            b["gruppe"] = key
        all_bookings.extend(bookings)

    # Index mit neu entdeckten Varianten aktualisieren
    entries = [{"full_key": base_key, "abbreviation": abbr, "semester": int(sem), "group_letter": ""}]
    for s, ok in zip(all_suffixes, probe_results):
        if ok:
            entries.append({"full_key": f"{base_key}.{s}", "abbreviation": abbr, "semester": int(sem), "group_letter": s})
    await db.save_course_index(entries)
    log.info("Brute-Force %s: %d Varianten, %d Einträge", base_key, len(valid_variants), len(all_bookings))

    label = date or f"KW {_date.today().isocalendar()[1]}"
    return {"course_semester": course_semester, "queried_date": label, "bookings": all_bookings}


async def _probe_course_key(key: str) -> bool:
    """Prüft ob ein course_semester-Key in der API existiert (200 = True, sonst False)."""
    try:
        token = await _get_token()
        async with _client(token) as c:
            r = await c.get(
                f"/api/v1/timetables/coursesemester/{key}",
                headers={"Accept": "text/calendar"},
            )
        return r.status_code == 200
    except Exception:
        return False


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
