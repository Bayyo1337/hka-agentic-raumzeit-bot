"""
Raumzeit API wrapper + Tool-Definitionen im OpenAI-Format (LiteLLM-kompatibel).
Base URL: https://raumzeit.hka-iwi.de
Auth: Bearer JWT via POST /private/api/v1/authentication
"""

import httpx
from src.config import settings

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
# API helpers
# ---------------------------------------------------------------------------

async def get_all_rooms() -> list:
    token = await _get_token()
    async with _client(token) as c:
        r = await c.get("/api/v1/rooms/all")
        r.raise_for_status()
        return r.json()


async def get_room_timetable(room_name: str, date: str | None = None) -> list:
    token = await _get_token()
    params = {"date": date} if date else {}
    async with _client(token) as c:
        r = await c.get(f"/api/v1/timetables/room/{room_name}", params=params)
        r.raise_for_status()
        return r.json()


async def get_course_timetable(course_semester: str) -> list:
    token = await _get_token()
    async with _client(token) as c:
        r = await c.get(f"/api/v1/timetables/coursesemester/{course_semester}")
        r.raise_for_status()
        return r.json()


async def get_lecturer_timetable(account: str) -> list:
    token = await _get_token()
    async with _client(token) as c:
        r = await c.get(f"/api/v1/timetables/lecturer/{account}")
        r.raise_for_status()
        return r.json()


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
        return r.json()


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
            "description": "Gibt den Stundenplan eines Kurs-Semesters zurück, z.B. 'IWI_3'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_semester": {
                        "type": "string",
                        "description": "Kurs-Semester-Bezeichner, z.B. 'IWI_3' oder 'MIB_1'.",
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
    "get_course_timetable":    lambda inp: get_course_timetable(inp["course_semester"]),
    "get_lecturer_timetable":  lambda inp: get_lecturer_timetable(inp["account"]),
    "get_departments":         lambda inp: get_departments(),
    "get_courses_of_study":    lambda inp: get_courses_of_study(inp.get("faculty")),
    "get_university_calendar": lambda inp: get_university_calendar(),
}
