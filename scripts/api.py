"""
Raumzeit API Explorer – interaktives Terminal-Tool.

Menü-Modus:   uv run python scripts/api.py
Direkt-Modus: uv run python scripts/api.py room F-001 2026-04-10
              uv run python scripts/api.py course MABB.7
              uv run python scripts/api.py lecturer muster
              uv run python scripts/api.py rooms
              uv run python scripts/api.py departments
              uv run python scripts/api.py courses [fakultaet]
              uv run python scripts/api.py calendar
              uv run python scripts/api.py token
              uv run python scripts/api.py raw GET /api/v1/rooms/all
"""

import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import httpx


def _load_env(path: Path) -> None:
    """Minimaler .env-Parser – kein python-dotenv nötig."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_env(Path(__file__).parent.parent / ".env")

BASE_URL = os.getenv("RAUMZEIT_BASE_URL", "https://raumzeit.hka-iwi.de")
LOGIN    = os.getenv("RAUMZEIT_LOGIN", "")
PASSWORD = os.getenv("RAUMZEIT_PASSWORD", "")

BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[0;36m"
GREEN  = "\033[0;32m"
YELLOW = "\033[0;33m"
RED    = "\033[0;31m"
NC     = "\033[0m"

TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hr(title: str = "") -> None:
    width = 60
    if title:
        pad = "─" * max(0, width - len(title) - 4)
        print(f"\n{BOLD}{CYAN}── {title} {pad}{NC}")
    else:
        print(f"{DIM}{'─' * width}{NC}")


def ok(msg: str)   -> None: print(f"  {GREEN}✓  {msg}{NC}")
def err(msg: str)  -> None: print(f"  {RED}✗  {msg}{NC}")
def info(msg: str) -> None: print(f"  {DIM}{msg}{NC}")
def ask(prompt: str) -> str: return input(f"{YELLOW}▶ {prompt}{NC} ").strip()


def pjson(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def status_line(r: httpx.Response) -> None:
    ct = r.headers.get("content-type", "?")
    color = GREEN if r.status_code < 300 else (YELLOW if r.status_code < 500 else RED)
    print(f"  {color}HTTP {r.status_code}{NC}  {DIM}{ct}  {len(r.content)} bytes{NC}\n")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_token_cache: str | None = None


async def get_token() -> str:
    global _token_cache
    if _token_cache:
        return _token_cache
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.post(
            "/private/api/v1/authentication",
            json={"login": LOGIN, "password": PASSWORD},
        )
        r.raise_for_status()
        _token_cache = r.json()["accessToken"]
        return _token_cache


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Text-format parser  (weekday#start_min#end_min#course_id#name)
# ---------------------------------------------------------------------------

_DAYS = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}


def parse_text_timetable(text: str) -> list[dict]:
    entries = []
    for line in text.strip().splitlines():
        parts = line.split("#")
        if len(parts) < 5:
            continue
        try:
            day   = int(parts[0])
            s_min = int(parts[1])
            e_min = int(parts[2])
            entries.append({
                "day":    _DAYS.get(day, str(day)),
                "start":  f"{s_min // 60:02d}:{s_min % 60:02d}",
                "end":    f"{e_min // 60:02d}:{e_min % 60:02d}",
                "course": parts[3],
                "name":   parts[4].strip(),
            })
        except (ValueError, IndexError):
            continue
    return entries


def print_text_timetable(entries: list[dict], filter_date: str | None = None) -> None:
    if filter_date:
        try:
            d = date.fromisoformat(filter_date)
            wd = d.weekday() + 1
            entries = [e for e in entries if e["day"] == _DAYS.get(wd)]
        except ValueError:
            pass

    if not entries:
        info("Keine Belegungen.")
        return

    by_day: dict[str, list] = {}
    for e in entries:
        by_day.setdefault(e["day"], []).append(e)

    day_order = list(_DAYS.values())
    for day in day_order:
        if day not in by_day:
            continue
        print(f"  {BOLD}{day}{NC}")
        for e in sorted(by_day[day], key=lambda x: x["start"]):
            print(f"    {GREEN}{e['start']}–{e['end']}{NC}  {e['name']}  {DIM}[{e['course']}]{NC}")


# ---------------------------------------------------------------------------
# iCal parser
# ---------------------------------------------------------------------------

def parse_ical(text: str) -> list[dict]:
    events, cur = [], {}
    seen: set[tuple] = set()
    for line in text.splitlines():
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur:
                key = (cur.get("start"), cur.get("end"), cur.get("name"), cur.get("room"))
                if key not in seen:
                    seen.add(key)
                    events.append(cur)
        elif line.startswith("SUMMARY:"):
            cur["name"] = line[8:].strip()
        elif line.startswith("DTSTART"):
            val = line.split(":", 1)[-1].rstrip("Z")
            if ":" in val:
                val = val.split(":")[-1].rstrip("Z")
            cur["start"] = val
        elif line.startswith("DTEND"):
            val = line.split(":", 1)[-1].rstrip("Z")
            if ":" in val:
                val = val.split(":")[-1].rstrip("Z")
            cur["end"] = val
        elif line.startswith("LOCATION:"):
            cur["room"] = line[9:].strip()
        elif line.startswith("CONTACT:"):
            cur["contact"] = line[8:].strip()
    return events


def extract_contacts(text: str) -> set[str]:
    """Extrahiert alle CONTACT-Kürzel aus einem iCal (auch komma-getrennte Mehrfachwerte)."""
    contacts = set()
    for line in text.splitlines():
        if line.startswith("CONTACT:"):
            for val in line[8:].split(","):
                val = val.strip()
                if val:
                    contacts.add(val)
    return contacts


def fmt_time(s: str) -> str:
    """'20260410T113000' → '11:30'"""
    return f"{s[9:11]}:{s[11:13]}" if len(s) >= 13 else s


def print_ical_events(events: list[dict], filter_date: str | None = None) -> None:
    if filter_date:
        compact = filter_date.replace("-", "")
        events = [e for e in events if e.get("start", "").startswith(compact)]

    if not events:
        info("Keine Einträge.")
        return

    by_date: dict[str, list] = {}
    for e in events:
        d = e.get("start", "")[:8]
        by_date.setdefault(d, []).append(e)

    for d in sorted(by_date):
        label = f"{d[6:8]}.{d[4:6]}.{d[:4]}" if len(d) == 8 else d
        print(f"\n  {BOLD}{label}{NC}")
        for e in sorted(by_date[d], key=lambda x: x.get("start", "")):
            room = f"  {DIM}{e.get('room', '')}{NC}" if e.get("room") else ""
            print(f"    {GREEN}{fmt_time(e['start'])}–{fmt_time(e['end'])}{NC}  {e.get('name', '')}{room}")


# ---------------------------------------------------------------------------
# API commands
# ---------------------------------------------------------------------------

async def cmd_token() -> None:
    hr("JWT Token")
    token = await get_token()
    ok(f"{token[:40]}…{token[-10:]}")
    info(f"Länge: {len(token)} Zeichen")


async def cmd_room(room: str, filter_date: str | None = None) -> None:
    label = filter_date or "aktuelle Woche"
    hr(f"Raum: {room}  [{label}]")
    token = await get_token()
    params = {"date": filter_date} if filter_date else {}
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get(f"/api/v1/timetables/room/{room}", headers=auth_headers(token), params=params)
    status_line(r)
    if r.status_code == 404:
        err(f"Raum '{room}' nicht gefunden.")
        return
    r.raise_for_status()

    if not r.text.strip():
        info("Keine Belegungen.")
        return

    try:
        data = r.json()
        if isinstance(data, list):
            if not data:
                info("Keine Belegungen.")
            else:
                pjson(data)
        else:
            pjson(data)
    except Exception:
        entries = parse_text_timetable(r.text)
        print_text_timetable(entries, filter_date)


async def cmd_course(course_semester: str, filter_date: str | None = None) -> None:
    label = filter_date or "alle Termine"
    hr(f"Kurs: {course_semester}  [{label}]")
    token = await get_token()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get(
            f"/api/v1/timetables/coursesemester/{course_semester}",
            headers={**auth_headers(token), "Accept": "text/calendar"},
        )
    status_line(r)
    if r.status_code == 404:
        err(f"Kurs '{course_semester}' nicht gefunden.")
        return
    r.raise_for_status()

    events = parse_ical(r.text)
    info(f"{len(events)} Event(s) gesamt")
    print_ical_events(events, filter_date)


async def cmd_lecturer(account: str, filter_date: str | None = None) -> None:
    label = filter_date or "alle Termine"
    hr(f"Dozent: {account}  [{label}]")
    token = await get_token()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get(f"/api/v1/timetables/lecturer/{account}", headers=auth_headers(token))
    status_line(r)
    if r.status_code == 404:
        err(f"Dozent '{account}' nicht gefunden. Format: tama0001 (2x Nachname + 2x Vorname + 4 Ziffern)")
        return
    r.raise_for_status()
    events = parse_ical(r.text)
    info(f"{len(events)} Event(s) gesamt")
    print_ical_events(events, filter_date)


async def cmd_rooms() -> None:
    hr("Alle Räume")
    token = await get_token()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get("/api/v1/rooms/all", headers=auth_headers(token))
    status_line(r)
    r.raise_for_status()
    data = r.json()
    names = sorted(
        (item.get("name") or item.get("shortName") or str(item)) if isinstance(item, dict) else str(item)
        for item in data
    )
    info(f"{len(names)} Räume")
    col, cols = 0, 6
    for n in names:
        print(f"  {n:12s}", end="")
        col += 1
        if col % cols == 0:
            print()
    if col % cols != 0:
        print()


async def cmd_departments() -> None:
    hr("Departments / Fakultäten")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get("/api/v1/departments/public")
    status_line(r)
    r.raise_for_status()
    pjson(r.json())


async def cmd_courses_of_study(faculty: str | None = None) -> None:
    path = f"/api/v1/coursesofstudy/public/{faculty}" if faculty else "/api/v1/coursesofstudy/public"
    hr("Studiengänge" + (f" [{faculty}]" if faculty else ""))
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get(path)
    status_line(r)
    r.raise_for_status()
    data = r.json()
    info(f"{len(data)} Studiengänge")
    for item in data:
        if isinstance(item, dict):
            short = item.get("name", "")
            long_ = item.get("longName", "")
            print(f"  {BOLD}{short:12s}{NC} {long_}")
        else:
            print(f"  {item}")


async def cmd_calendar() -> None:
    hr("Hochschulkalender")
    token = await get_token()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get("/api/v1/universitycalendar/", headers=auth_headers(token))
    status_line(r)
    r.raise_for_status()
    pjson(r.json())


def _time_to_min(hhmm: str) -> int:
    try:
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return 0


def _min_to_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _free_slots(entries: list[dict], day_start: int = 480, day_end: int = 1200) -> list[tuple[str, str]]:
    """Berechnet freie Zeitfenster. day_start/end in Minuten (480=08:00, 1200=20:00)."""
    occupied = sorted(
        (_time_to_min(e["start"]), _time_to_min(e["end"]))
        for e in entries
        if e.get("start") and e.get("end")
    )
    free, cursor = [], day_start
    for s, e in occupied:
        if s > cursor:
            free.append((_min_to_time(cursor), _min_to_time(s)))
        cursor = max(cursor, e)
    if cursor < day_end:
        free.append((_min_to_time(cursor), _min_to_time(day_end)))
    return free


async def cmd_scan(filter_date: str | None = None, count: int = 15) -> None:
    target = filter_date or TODAY
    try:
        d_obj = date.fromisoformat(target)
    except ValueError:
        err(f"Ungültiges Datum: {target}")
        return

    weekday_str = _DAYS.get(d_obj.weekday() + 1, "?")
    day_label   = f"{weekday_str}, {d_obj.day:02d}.{d_obj.month:02d}.{d_obj.year}"
    hr(f"Raum-Scan  [{day_label}]  n={count}")

    # 1. Alle Räume laden
    token = await get_token()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get("/api/v1/rooms/all", headers=auth_headers(token))
    r.raise_for_status()
    all_names = []
    for item in r.json():
        n = (item.get("name") or item.get("shortName")) if isinstance(item, dict) else str(item)
        if n:
            all_names.append(n)

    import random
    sample = random.sample(all_names, min(count, len(all_names)))
    info(f"{len(all_names)} Räume bekannt → {len(sample)} zufällig ausgewählt")
    print()

    # 2. In 10er-Batches abfragen
    async def fetch(client: httpx.AsyncClient, room_name: str) -> tuple[str, list[dict]]:
        try:
            resp = await client.get(
                f"/api/v1/timetables/room/{room_name}",
                headers=auth_headers(token),
                params={"date": target},
            )
            if resp.status_code != 200 or not resp.text.strip():
                return room_name, []
            try:
                data = resp.json()
                entries = []
                for e in (data if isinstance(data, list) else []):
                    if not isinstance(e, dict):
                        continue
                    start = e.get("startTime") or e.get("start", "")
                    end   = e.get("endTime")   or e.get("end", "")
                    name  = e.get("name") or e.get("longName", "")
                    if "T" in start:
                        start = start.split("T")[1][:5]
                        end   = end.split("T")[1][:5] if "T" in end else end[:5]
                    entries.append({"start": start, "end": end, "name": name, "day": weekday_str})
                return room_name, entries
            except Exception:
                entries = parse_text_timetable(resp.text)
                return room_name, [e for e in entries if e["day"] == weekday_str]
        except Exception:
            return room_name, []

    BATCH = 10
    results: list[tuple[str, list[dict]]] = []
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as client:
        for i in range(0, len(sample), BATCH):
            batch = sample[i:i + BATCH]
            info(f"Batch {i // BATCH + 1}/{-(-len(sample) // BATCH)}  ({', '.join(batch)})")
            results.extend(await asyncio.gather(*[fetch(client, r) for r in batch]))

    # 3. Sortieren: frei / belegt
    free_rooms  = [(name, entries) for name, entries in results if not entries]
    busy_rooms  = [(name, entries) for name, entries in results if entries]
    busy_rooms.sort(key=lambda x: x[0])
    free_rooms.sort(key=lambda x: x[0])

    # 4. Ausgabe – jeder Raum einzeln mit allen Blöcken
    all_results = sorted(free_rooms + busy_rooms, key=lambda x: x[0])
    free_count  = len(free_rooms)
    busy_count  = len(busy_rooms)
    info(f"{GREEN}{busy_count} belegt{NC}  {DIM}|{NC}  {GREEN}{free_count} frei{NC}")

    DAY_START, DAY_END = 480, 1200  # 08:00 – 20:00

    for name, entries in all_results:
        sorted_entries = sorted(entries, key=lambda e: e["start"])
        free_slots     = _free_slots(sorted_entries, DAY_START, DAY_END)
        status         = f"{GREEN}frei{NC}" if not entries else f"{RED}belegt{NC}"
        print(f"\n  {BOLD}{name:14s}{NC}  {status}")

        if not entries:
            print(f"    {GREEN}08:00–20:00  (ganztägig frei){NC}")
            continue

        # Alle Blöcke in chronologischer Reihenfolge mischen
        blocks: list[tuple[str, str, str, bool]] = []  # (start, end, label, is_free)
        for s, e in free_slots:
            blocks.append((s, e, "(frei)", True))
        for e in sorted_entries:
            label = e.get("name", "")
            if e.get("course"):
                label += f" [{e['course']}]"
            blocks.append((e["start"], e["end"], label, False))
        blocks.sort(key=lambda b: b[0])

        for start, end, label, is_free in blocks:
            if is_free:
                print(f"    {GREEN}{start}–{end}{NC}  {DIM}{label}{NC}")
            else:
                print(f"    {RED}{start}–{end}{NC}  {label}")


async def cmd_contacts(semesters: list[int] | None = None) -> None:
    """Scannt Kurs-iCals und sammelt alle CONTACT-Kürzel (= Dozenten-Accounts)."""
    if semesters is None:
        semesters = list(range(1, 8))
    hr(f"Dozenten-Kürzel Scanner  [Semester {semesters}]")

    # Studiengänge laden
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.get("/api/v1/coursesofstudy/public")
    r.raise_for_status()
    abbreviations = [item["name"] for item in r.json() if isinstance(item, dict) and item.get("name")]
    info(f"{len(abbreviations)} Studiengänge, {len(semesters)} Semester → max. {len(abbreviations) * len(semesters)} Kurs-Keys")

    token = await get_token()
    all_contacts: dict[str, set[str]] = {}  # kürzel → set of course_keys

    async def fetch_contacts(client: httpx.AsyncClient, key: str) -> tuple[str, set[str]]:
        try:
            r = await client.get(
                f"/api/v1/timetables/coursesemester/{key}",
                headers={**auth_headers(token), "Accept": "text/calendar"},
            )
            if r.status_code != 200:
                return key, set()
            return key, extract_contacts(r.text)
        except Exception:
            return key, set()

    keys = [f"{abbr}.{sem}" for abbr in abbreviations for sem in semesters]
    BATCH = 20
    for i in range(0, len(keys), BATCH):
        batch = keys[i:i + BATCH]
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as client:
            results = await asyncio.gather(*[fetch_contacts(client, k) for k in batch])
        for key, contacts in results:
            for c in contacts:
                all_contacts.setdefault(c, set()).add(key)
        print(f"  {DIM}Batch {i // BATCH + 1}/{-(-len(keys) // BATCH)} ({len(all_contacts)} Kürzel bisher){NC}", end="\r")

    print()
    info(f"{len(all_contacts)} Dozenten-Kürzel gefunden:\n")
    for contact in sorted(all_contacts):
        courses = ", ".join(sorted(all_contacts[contact])[:5])
        if len(all_contacts[contact]) > 5:
            courses += f" +{len(all_contacts[contact]) - 5}"
        print(f"  {BOLD}{contact:15s}{NC}  {DIM}{courses}{NC}")


def _normalize(s: str) -> str:
    """Umlaute + Sonderzeichen → ASCII-Kleinbuchstaben für Kürzel-Vergleich."""
    s = s.lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z]", "", s)


def _kandidaten(vorname: str, nachname: str) -> list[str]:
    """Generiert mögliche Kürzel: [2×Nachname][2×Vorname] mit Nummern 0001–0010."""
    v = _normalize(vorname)
    n = _normalize(nachname)
    if len(v) < 2 or len(n) < 2:
        return []
    prefix = n[:2] + v[:2]
    return [f"{prefix}{i:04d}" for i in range(1, 11)]


async def cmd_hka_debug() -> None:
    """Zeigt die rohe HTML der HKA-Personenliste zur Diagnose."""
    hr("HKA Personen-Seite – Raw HTML")
    async with httpx.AsyncClient(base_url="https://www.h-ka.de", timeout=20, follow_redirects=True) as c:
        r = await c.get(
            "/die-hochschule-karlsruhe/organisation-personen/personen-a-z",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )
    status_line(r)
    html = r.text
    info(f"Gesamt: {len(html)} bytes")

    # Korrekte E-Mail-Regex (span-Obfuskierung)
    emails_found = re.findall(r'([\w.\-]+)<span[^>]*>spam prevention</span>@h-ka\.de', html)
    info(f"E-Mail-Treffer (span-Regex): {len(emails_found)}")

    # Kontext um ersten Treffer zeigen
    idx = html.find("spam prevention")
    if idx >= 0:
        print(f"\n{DIM}── Kontext ±500 Zeichen um erstes Vorkommen ──{NC}")
        print(html[max(0, idx-500):idx+200])

    if emails_found:
        print(f"\n{DIM}── Erste 5 E-Mail-Usernames ──{NC}")
        for e in emails_found[:5]:
            print(f"  {e}@h-ka.de")


async def cmd_match() -> None:
    """Scrapt die HKA-Personenliste und matcht sie gegen bekannte Dozenten-Kürzel."""
    hr("Personen-Matching  [h-ka.de ↔ Raumzeit-Kürzel]")
    info("Starte Aufbau (kann ~2 Min dauern)…")

    sys.path.insert(0, str(Path(__file__).parent.parent))
    import src.tools as _tools  # noqa: PLC0415

    count = await _tools.build_lecturer_index()
    ok(f"{count} Dozenten-Kürzel gematcht und in data/lecturers.json gespeichert\n")

    for kuerzel, data in sorted(_tools._LECTURERS.items(), key=lambda x: x[1]["name"]):
        print(f"  {BOLD}{kuerzel:15s}{NC}  {data['name']:30s}  {DIM}{data['email']}{NC}")


async def cmd_raw(method: str, path: str) -> None:
    hr(f"RAW {method.upper()} {path}")
    token = await get_token()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        r = await c.request(method.upper(), path, headers=auth_headers(token))
    status_line(r)
    try:
        pjson(r.json())
    except Exception:
        print(r.text[:4000])


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

MENU = """
{bold}{cyan}  Raumzeit API Explorer{nc}  {dim}({base}){nc}

  1) Raum-Belegung
  2) Kurs-Stundenplan  (iCal)
  3) Dozenten-Stundenplan
  4) Alle Räume auflisten
  5) Studiengänge
  6) Departments / Fakultäten
  7) Hochschulkalender
  8) JWT Token anzeigen
  9) Raw HTTP Request
  s) Zufälligen Raum-Scan starten
  d) Dozenten-Kürzel scannen
  m) Personen-Matching (h-ka.de ↔ Raumzeit)
  x) HKA-Seite debuggen (rohe HTML)
  0) Beenden
"""


async def interactive() -> None:
    print(MENU.format(bold=BOLD, cyan=CYAN, nc=NC, dim=DIM, base=BASE_URL))
    while True:
        choice = ask("Auswahl")
        try:
            if choice == "0":
                print("Tschüss!")
                break
            elif choice == "1":
                room = ask("Raum (z.B. F-001)")
                if not room:
                    continue
                d = ask(f"Datum YYYY-MM-DD  [Enter = aktuelle Woche, 'h' = heute ({TODAY})]")
                if d.lower() == "h":
                    d = TODAY
                await cmd_room(room, d or None)
            elif choice == "2":
                cs = ask("Kurs.Semester (z.B. MABB.7 oder INFB.3.A)")
                if not cs:
                    continue
                d = ask(f"Datum YYYY-MM-DD  [Enter = alle, 'h' = heute ({TODAY})]")
                if d.lower() == "h":
                    d = TODAY
                await cmd_course(cs, d or None)
            elif choice == "3":
                acc = ask("Account-Kürzel (z.B. tama0001)")
                if not acc:
                    continue
                d = ask(f"Datum YYYY-MM-DD  [Enter = alle, 'h' = heute ({TODAY})]")
                if d.lower() == "h":
                    d = TODAY
                await cmd_lecturer(acc, d or None)
            elif choice == "4":
                await cmd_rooms()
            elif choice == "5":
                fac = ask("Fakultät filtern  [Enter = alle]")
                await cmd_courses_of_study(fac or None)
            elif choice == "6":
                await cmd_departments()
            elif choice == "7":
                await cmd_calendar()
            elif choice == "8":
                await cmd_token()
            elif choice == "9":
                method = ask("Methode (GET/POST)")
                path   = ask("Pfad (z.B. /api/v1/rooms/all)")
                if method and path:
                    await cmd_raw(method, path)
            elif choice == "m":
                await cmd_match()
            elif choice == "x":
                await cmd_hka_debug()
            elif choice == "d":
                sem_str = ask("Semester filtern (z.B. '1,2,3') [Enter = alle 1–7]")
                sems = [int(s.strip()) for s in sem_str.split(",") if s.strip().isdigit()] or None
                await cmd_contacts(sems)
            elif choice == "s":
                d = ask(f"Datum YYYY-MM-DD  [Enter = heute ({TODAY}), 'h' = heute]")
                if not d or d.lower() == "h":
                    d = TODAY
                n_str = ask("Anzahl Räume  [Enter = 15]")
                n = int(n_str) if n_str.isdigit() else 15
                await cmd_scan(d, n)
            else:
                err("Unbekannte Auswahl.")
        except httpx.HTTPStatusError as e:
            err(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        except KeyboardInterrupt:
            print("\nTschüss!")
            break
        except Exception as e:
            err(str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    args = sys.argv[1:]

    if not args:
        await interactive()
        return

    cmd = args[0].lower()
    try:
        if cmd == "token":
            await cmd_token()
        elif cmd == "room":
            if len(args) < 2:
                err("Verwendung: api.py room <name> [datum]")
                return
            await cmd_room(args[1], args[2] if len(args) > 2 else None)
        elif cmd == "course":
            if len(args) < 2:
                err("Verwendung: api.py course <kurs.sem> [datum]")
                return
            await cmd_course(args[1], args[2] if len(args) > 2 else None)
        elif cmd == "lecturer":
            if len(args) < 2:
                err("Verwendung: api.py lecturer <account> [datum]")
                return
            await cmd_lecturer(args[1], args[2] if len(args) > 2 else None)
        elif cmd == "rooms":
            await cmd_rooms()
        elif cmd == "departments":
            await cmd_departments()
        elif cmd in ("courses", "coursesofstudy"):
            await cmd_courses_of_study(args[1] if len(args) > 1 else None)
        elif cmd == "calendar":
            await cmd_calendar()
        elif cmd == "scan":
            d = args[1] if len(args) > 1 else TODAY
            n = int(args[2]) if len(args) > 2 and args[2].isdigit() else 15
            await cmd_scan(d, n)
        elif cmd in ("match", "personen"):
            await cmd_match()
        elif cmd in ("contacts", "dozenten"):
            sems = [int(a) for a in args[1:] if a.isdigit()] or None
            await cmd_contacts(sems)
        elif cmd == "raw":
            if len(args) < 3:
                err("Verwendung: api.py raw <METHOD> <pfad>")
                return
            await cmd_raw(args[1], args[2])
        else:
            err(f"Unbekannter Befehl: {cmd}")
            print(__doc__)
            sys.exit(1)
    except httpx.HTTPStatusError as e:
        err(f"HTTP {e.response.status_code}")
        print(e.response.text[:500])
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        err(str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
