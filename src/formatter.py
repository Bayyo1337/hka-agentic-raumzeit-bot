"""
Python-Formatter: wandelt Tool-Ergebnisse in lesbaren Telegram-Text um.
Das LLM wählt nur Tools aus – die Präsentation macht dieser Modul.
"""

from datetime import date as _date, datetime as _datetime

_WEEKDAY_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Tools die nur als Zwischenschritt dienen (kein eigenes Format nötig)
_LOOKUP_TOOLS = {"get_courses_of_study", "get_all_rooms", "get_departments"}


def _fmt_date(iso_date: str) -> str:
    """'2026-04-13' → 'Mo, 13.04.2026'"""
    try:
        d = _date.fromisoformat(iso_date)
        return f"{_WEEKDAY_DE[d.weekday()]}, {d.day:02d}.{d.month:02d}.{d.year}"
    except (ValueError, IndexError):
        return iso_date


def _to_hhmm(time_str: str) -> str:
    """Normalisiert Zeit auf 'HH:MM'. Akzeptiert 'HH:MM', 'HH:MM:SS' und ISO-Datetime."""
    if not time_str:
        return ""
    if "T" in time_str:
        time_str = time_str.split("T")[1]
    return time_str[:5]


def _time_to_minutes(hhmm: str) -> int:
    """'09:50' → 590"""
    try:
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return 0


def _minutes_to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _dedup_bookings(bookings: list[dict]) -> list[dict]:
    """Entfernt Duplikate mit gleicher start+end+name-Kombination."""
    seen: set[tuple] = set()
    result = []
    for b in bookings:
        key = (_to_hhmm(b.get("start", "")), _to_hhmm(b.get("end", "")), b.get("name", ""))
        if key not in seen:
            seen.add(key)
            result.append(b)
    return result


def _free_slots(bookings: list[dict], day_start: str = "08:00", day_end: str = "20:00") -> list[tuple[str, str]]:
    """Berechnet freie Zeitfenster zwischen Belegungen."""
    occupied = []
    for b in bookings:
        s = _time_to_minutes(_to_hhmm(b.get("start", "")))
        e = _time_to_minutes(_to_hhmm(b.get("end", "")))
        if s and e and e > s:
            occupied.append((s, e))
    occupied.sort()

    free = []
    cursor = _time_to_minutes(day_start)
    end_of_day = _time_to_minutes(day_end)
    for s, e in occupied:
        if s > cursor:
            free.append((_minutes_to_hhmm(cursor), _minutes_to_hhmm(s)))
        cursor = max(cursor, e)
    if cursor < end_of_day:
        free.append((_minutes_to_hhmm(cursor), _minutes_to_hhmm(end_of_day)))
    return free


# ── Einzelne Formatter ───────────────────────────────────────────────────────

def _fmt_room(result: dict) -> str:
    room = result.get("room", "?")
    queried_date = result.get("queried_date", "")
    bookings = result.get("bookings", [])

    if "error" in result:
        return f"❌ {result['error']}"

    date_label = _fmt_date(queried_date) if queried_date and queried_date != "aktuelle Woche" else queried_date
    lines = [f"🏫 *{room}*" + (f" – {date_label}" if date_label else "")]

    if not bookings:
        lines.append("✅ Ganztägig frei")
        return "\n".join(lines)

    bookings_sorted = sorted(_dedup_bookings(bookings), key=lambda b: _to_hhmm(b.get("start", "")))
    for b in bookings_sorted:
        start = _to_hhmm(b.get("start", ""))
        end = _to_hhmm(b.get("end", ""))
        name = b.get("name", "")
        lines.append(f"🔴 {start}–{end} {name}")

    free = _free_slots(bookings_sorted)
    if free:
        free_str = " · ".join(f"{s}–{e}" for s, e in free)
        lines.append(f"\n✅ Frei: {free_str}")

    return "\n".join(lines)


def _fmt_room_multi(results: list[dict]) -> str:
    """Mehrere Tage für denselben Raum."""
    parts = []
    for r in results:
        parts.append(_fmt_room(r))
    return "\n\n".join(parts)


def _fmt_course(result: dict) -> str:
    if "error" in result:
        return f"❌ {result['error']}"

    course = result.get("course_semester", "?")
    queried_date = result.get("queried_date", "")
    bookings = result.get("bookings", [])

    if not bookings:
        date_label = _fmt_date(queried_date) if queried_date and queried_date != "aktuelles Semester" else queried_date
        base = f"📅 *{course}*: Keine Einträge" + (f" für {date_label}" if date_label else "") + "."
        return base + "\n\n❓ Stimmt das so? (ja / nein)"

    # Gruppiere nach Datum → Gruppe
    from collections import defaultdict
    by_date: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for b in bookings:
        date_str = ""
        start = b.get("start", "")
        if "T" in start:
            date_str = start.split("T")[0]
        gruppe = b.get("gruppe", course)
        by_date[date_str][gruppe].append(b)

    lines = [f"📅 *Stundenplan {course}*"]
    for date_str in sorted(by_date):
        date_label = _fmt_date(date_str) if date_str else "Unbekanntes Datum"
        lines.append(f"\n*{date_label}*")
        for gruppe in sorted(by_date[date_str]):
            gruppe_bookings = sorted(by_date[date_str][gruppe], key=lambda b: b.get("start", ""))
            if len(by_date[date_str]) > 1:
                lines.append(f"  _{gruppe}_")
            for b in gruppe_bookings:
                start = _to_hhmm(b.get("start", ""))
                end = _to_hhmm(b.get("end", ""))
                name = b.get("name", "")
                room = b.get("room", "")
                room_suffix = f" 🏫{room}" if room else ""
                lines.append(f"  {start}–{end} {name}{room_suffix}")

    return "\n".join(lines)


def _fmt_lecturer(result: dict) -> str:
    if "error" in result:
        return f"❌ {result['error']}"

    lecturer = result.get("lecturer", "?")
    bookings = result.get("bookings", [])

    lines = [f"👤 *Stundenplan {lecturer}*"]
    if not bookings:
        lines.append("Keine Einträge gefunden.")
        return "\n".join(lines)

    for b in sorted(bookings, key=lambda b: b.get("start", "")):
        start = _to_hhmm(b.get("start", ""))
        end = _to_hhmm(b.get("end", ""))
        name = b.get("name", "")
        lines.append(f"🔴 {start}–{end} {name}")

    return "\n".join(lines)


def _fmt_list(result) -> str:
    if isinstance(result, dict) and "error" in result:
        return f"❌ {result['error']}"

    items = result if isinstance(result, list) else []
    if not items:
        return "Keine Einträge gefunden."

    lines = []
    for item in items[:30]:
        if isinstance(item, dict):
            name = item.get("longName") or item.get("name", str(item))
            short = item.get("name", "")
            if short and short != name:
                lines.append(f"• {name} ({short})")
            else:
                lines.append(f"• {name}")
        else:
            lines.append(f"• {item}")

    if len(items) > 30:
        lines.append(f"… und {len(items) - 30} weitere")

    return "\n".join(lines)


def _fmt_calendar(result) -> str:
    items = result if isinstance(result, list) else []
    if not items:
        return "Kein Hochschulkalender verfügbar."

    lines = ["📆 *Hochschulkalender*"]
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        name = item.get("name", item.get("title", ""))
        start = item.get("start", item.get("startDate", ""))
        end = item.get("end", item.get("endDate", ""))
        if start:
            start = _fmt_date(start[:10]) if len(start) >= 10 else start
        if end:
            end = _fmt_date(end[:10]) if len(end) >= 10 else end
        if start and end and start != end:
            lines.append(f"• {name}: {start} – {end}")
        elif start:
            lines.append(f"• {name}: {start}")
        else:
            lines.append(f"• {name}")

    return "\n".join(lines)


# ── Haupt-Dispatcher ─────────────────────────────────────────────────────────

_FORMATTERS = {
    "get_room_timetable":      _fmt_room,
    "get_course_timetable":    _fmt_course,
    "get_lecturer_timetable":  _fmt_lecturer,
    "get_university_calendar": _fmt_calendar,
    "get_departments":         _fmt_list,
    "get_courses_of_study":    _fmt_list,
    "get_all_rooms":           _fmt_list,
}


def format_results(collected: list[tuple[str, dict]], user_message: str) -> str:
    """
    Formatiert alle gesammelten Tool-Ergebnisse zu einer Telegram-Antwort.

    Logik:
    - Mehrere get_room_timetable-Calls (Mehrtagesabfrage) → kombiniert
    - Lookup-Tools (get_courses_of_study etc.) werden nur angezeigt wenn es
      das einzige Ergebnis ist
    - Letztes Daten-Tool gewinnt bei gemischten Calls
    """
    if not collected:
        return "Ich konnte keine Daten abrufen. Bitte versuche es erneut."

    # Mehrere room_timetable-Calls zusammenfassen
    room_calls = [(n, r) for n, r in collected if n == "get_room_timetable"]
    if len(room_calls) > 1:
        return _fmt_room_multi([r for _, r in room_calls])

    # Letztes Nicht-Lookup-Tool bevorzugen
    data_calls = [(n, r) for n, r in collected if n not in _LOOKUP_TOOLS]
    if data_calls:
        name, result = data_calls[-1]
        fmt = _FORMATTERS.get(name)
        return fmt(result) if fmt else str(result)

    # Fallback: letztes Tool egal welches
    name, result = collected[-1]
    fmt = _FORMATTERS.get(name)
    return fmt(result) if fmt else str(result)
