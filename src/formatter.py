"""
Python-Formatter: wandelt Tool-Ergebnisse in lesbaren Telegram-Text um.
Das LLM wählt nur Tools aus – die Präsentation macht dieser Modul.
"""

from datetime import date as _date

_WEEKDAY_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Tools die nur als Zwischenschritt dienen (kein eigenes Format nötig)
_LOOKUP_TOOLS = {"get_courses_of_study", "get_all_rooms", "get_departments"}

# Sentinel string used by the escalation logic in bot.py to detect empty course results
CONFIRM_SENTINEL = "❓ Stimmt das so? (ja / nein)"


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
    """Entfernt/Aggregiert Duplikate mit gleicher Zeit/Raum-Kombination."""
    merged = []
    
    import re
    def _norm_mod(m: str) -> str:
        return re.sub(r'[^a-z0-9]', '', str(m).lower())
        
    for b in bookings:
        start = _to_hhmm(b.get("start", ""))
        end = _to_hhmm(b.get("end", ""))
        room = b.get("room", "")
        name = b.get("name", "")
        module = b.get("module", "")
        lecturer = b.get("lecturer", "")
        date_str = b.get("date", "")
        
        found = False
        for m in merged:
            m_start = _to_hhmm(m.get("start", ""))
            m_end = _to_hhmm(m.get("end", ""))
            m_room = m.get("room", "")
            m_date = m.get("date", "")
            if m_start == start and m_end == end and m_room == room and m_date == date_str:
                # Prüfen, ob Dozent gleich ist ODER Modulname sehr ähnlich
                if (lecturer and m.get("lecturer") == lecturer) or \
                   (module and _norm_mod(module) in _norm_mod(m.get("module", ""))) or \
                   (m.get("module") and _norm_mod(m.get("module", "")) in _norm_mod(module)):
                    # Merge it!
                    names = m.get("name", "").split(", ")
                    if name not in names:
                        names.append(name)
                        m["name"] = ", ".join(names)
                    if len(module) > len(m.get("module", "")):
                        m["module"] = module
                    found = True
                    break
        if not found:
            merged.append(dict(b))
            
    return merged


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

def _render_timeline(bookings: list[dict], day_label: str = "", header_prefix: str = "") -> list[str]:
    """Erzeugt eine chronologische Timeline (🟢/🔴) für eine Liste von Belegungen."""
    lines = []
    if header_prefix:
        lines.append(f"{header_prefix}" + (f" – {day_label}" if day_label else ""))
    elif day_label:
        lines.append(f"\n*{day_label}:*")

    current_time = _time_to_minutes("08:00")
    end_of_day = _time_to_minutes("20:00")
    
    # Sortieren und Deduplizieren
    sorted_bookings = sorted(_dedup_bookings(bookings), key=lambda b: _time_to_minutes(_to_hhmm(b.get("start", ""))))

    if not sorted_bookings:
        if day_label:
            if "Sa" in day_label or "Samstag" in day_label:
                lines.append("Am Samstag finden keine Vorlesungen statt.")
            elif "So" in day_label or "Sonntag" in day_label:
                lines.append("Am Sonntag finden keine Vorlesungen statt.")
            else:
                lines.append("Keine Belegungen gefunden (möglicherweise frei).")
        else:
            lines.append("Keine Belegungen gefunden.")
        return lines

    for b in sorted_bookings:
        start_min = _time_to_minutes(_to_hhmm(b.get("start", "")))
        end_min = _time_to_minutes(_to_hhmm(b.get("end", "")))

        if start_min > current_time:
            lines.append(f"🟢 {_minutes_to_hhmm(current_time)}–{_minutes_to_hhmm(start_min)} frei")
        
        course_code = b.get("name", "")
        module = b.get("module", "")
        lecturer = b.get("lecturer", "")
        room = b.get("room", "")
        cancelled = b.get("cancelled", False)
        
        name_lower = f"{course_code} {module}".lower()
        if "fällt aus" in name_lower or "entfällt" in name_lower or "canceled" in name_lower:
            cancelled = True
        
        if module and module != course_code:
            label = f"*({course_code})* {module}"
        else:
            label = f"*{course_code}*"

        if lecturer:
            from src.tools import _LECTURERS
            resolved = []
            for k in str(lecturer).split(", "):
                k = k.strip()
                if k in _LECTURERS:
                    resolved.append(_LECTURERS[k].get("name", k))
                else:
                    resolved.append(k)
            label += f" ({', '.join(resolved)})"

        if room and not header_prefix.startswith("🏫"):
            label += f" 🏫 {room}"            

        time_range = f"{_to_hhmm(b.get('start', ''))}–{_to_hhmm(b.get('end', ''))}"
        if cancelled:
            lines.append(f"❌ ~{time_range} {label}~ (FÄLLT AUS)")
        else:
            lines.append(f"🔴 {time_range} {label}")
            
        current_time = max(current_time, end_min)
    
    if current_time < end_of_day:
        lines.append(f"🟢 {_minutes_to_hhmm(current_time)}–{_minutes_to_hhmm(end_of_day)} frei")
        
    return lines


def _fmt_room(result: dict) -> str:
    room = result.get("room", "?")
    queried_date = result.get("queried_date", "")
    bookings = result.get("bookings", [])

    if "error" in result:
        return f"❌ {result['error']}"

    if not bookings and not result.get("note"):
        date_label = _fmt_date(queried_date) if queried_date and queried_date != "aktuelle Woche" else queried_date
        return f"🏫 *{room}*" + (f" – {date_label}" if date_label else "") + "\n✅ Keine Belegungen gefunden (möglicherweise frei)"

    from collections import defaultdict
    by_day: dict[str, list] = defaultdict(list)
    for b in bookings:
        by_day[b.get("day") or ""].append(b)

    _day_order = {d: i for i, d in enumerate(_WEEKDAY_DE)}
    sorted_days = sorted(by_day.keys(), key=lambda d: _day_order.get(d, 99))

    all_lines = []
    if not sorted_days and result.get("note"):
        date_label = _fmt_date(queried_date) if queried_date and queried_date != "aktuelle Woche" else queried_date
        return f"🏫 *{room}*" + (f" – {date_label}" if date_label else "") + f"\n✅ Keine Belegungen gefunden.\n_{result['note']}_"

    for i, day in enumerate(sorted_days):
        date_label = _fmt_date(queried_date) if len(sorted_days) == 1 and queried_date and queried_date != "aktuelle Woche" else day
        if len(sorted_days) == 1:
            all_lines.extend(_render_timeline(by_day[day], date_label, f"🏫 *{room}*"))
        else:
            if i == 0: all_lines.append(f"🏫 *{room}* (Wochenübersicht)")
            all_lines.extend(_render_timeline(by_day[day], day))

    return "\n".join(all_lines)


def _fmt_room_multi(results: list[dict]) -> str:
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
        return base + "\n\n" + CONFIRM_SENTINEL

    from collections import defaultdict
    by_date: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for b in bookings:
        date_str = b.get("date") or ""
        if not date_str and "T" in b.get("start", ""):
            date_str = b["start"].split("T")[0]
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
    queried_date = result.get("queried_date", "")
    email = result.get("email")
    sprechzeit = result.get("sprechzeit")

    date_label = _fmt_date(queried_date) if queried_date and queried_date != "heute" else queried_date
    header = f"👤 *Stundenplan {lecturer}*" + (f" – {date_label}" if date_label else "")
    
    lines = [header]
    if email or sprechzeit:
        if email: lines.append(f"📧 {email}")
        if sprechzeit: lines.append(f"🕒 *Sprechzeit:* {sprechzeit}")
        lines.append("")

    if not bookings:
        lines.append("Keine Einträge für heute gefunden. An welchem Tag suchst du?")
        return "\n".join(lines)

    from collections import defaultdict
    by_day_room: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for b in bookings:
        d_name = b.get("day")
        if not d_name and b.get("date"):
            try:
                dt = _date.fromisoformat(b["date"])
                d_name = _WEEKDAY_DE[dt.weekday()]
            except: pass
        d_name = d_name or "Termine"
        room = b.get("room") or "Unbekannter Raum"
        by_day_room[d_name][room].append(b)

    _day_order = {d: i for i, d in enumerate(_WEEKDAY_DE)}
    sorted_days = sorted(by_day_room.keys(), key=lambda d: _day_order.get(d, 99))

    all_lines = []
    total_days = len(sorted_days)
    for day in sorted_days:
        rooms_on_day = by_day_room[day]
        for room in sorted(rooms_on_day.keys()):
            date_label = _fmt_date(queried_date) if total_days == 1 and queried_date and queried_date != "heute" else day
            deduplicated = _dedup_bookings(rooms_on_day[room])
            all_lines.extend(_render_timeline(deduplicated, date_label, f"🏫 *{room}*"))
            all_lines.append("")

    return "\n".join(all_lines).strip()


def _fmt_lecturer_info(result: dict) -> str:
    if "error" in result:
        return f"❌ {result['error']}"
    
    name = result.get("name", "?")
    email = result.get("email")
    sprechzeit = result.get("sprechzeit")
    
    lines = [f"👤 *Dozenten-Info: {name}*"]
    if email: lines.append(f"📧 E-Mail: {email}")
    if sprechzeit: lines.append(f"🕒 Sprechzeit: {sprechzeit}")
    if not email and not sprechzeit:
        lines.append("Keine Kontaktinformationen hinterlegt.")
    return "\n".join(lines)


def _fmt_mensa(result: dict) -> str:
    if "error" in result: return f"❌ {result['error']}"
    
    canteen = result.get("canteen", "Mensa")
    date_str = _fmt_date(result.get("date", ""))
    
    if result.get("closed"):
        return f"🍴 *{canteen}* – {date_str}\nDie Mensa ist an diesem Tag geschlossen oder es liegen keine Daten vor."
    
    meals = result.get("meals", [])
    if not meals:
        return f"🍴 *{canteen}* – {date_str}\nAktuell kein Speiseplan verfügbar."
    
    lines = [f"🍴 *{canteen}*", f"📅 {date_str}", ""]
    
    # Gruppieren nach Linie
    from collections import defaultdict
    lines_map = defaultdict(list)
    for m in meals:
        lines_map[m.get("line", {}).get("name", "Diverses")].append(m)
        
    for line_name in sorted(lines_map.keys()):
        lines.append(f"*{line_name}*")
        for m in lines_map[line_name]:
            icon = "🌱" if m.get("isVegan") else ("🥕" if m.get("isVegetarian") else "🥩")
            price = m.get("price", {}).get("student")
            price_str = f" ({price:.2f}€)" if price else ""
            lines.append(f"  {icon} {m['name']}{price_str}")
        lines.append("")
        
    lines.append("_Frage nach Details zu einem Gericht für Allergene._")
    return "\n".join(lines)


def _fmt_mensa_details(result: dict) -> str:
    if "error" in result: return f"❌ {result['error']}"
    
    name = result.get("name", "Unbekanntes Gericht")
    allergens = result.get("allergens", [])
    additives = result.get("additives", [])
    
    lines = [f"🍱 *{name}*", ""]
    if allergens:
        lines.append("*Allergene:*")
        lines.append(", ".join(allergens))
        lines.append("")
    if additives:
        lines.append("*Zusatzstoffe:*")
        lines.append(", ".join(additives))
        
    if not allergens and not additives:
        lines.append("Keine Allergene oder Zusatzstoffe gelistet.")
        
    return "\n".join(lines)


def _fmt_map(result: dict) -> str:
    building = result.get("building", "?")
    floor = result.get("floor", "unbekanntes Stockwerk")
    query = result.get("query", building)
    return f"📍 *Lageplan für {query}*\n\nDas Gebäude *{building}* befindet sich auf dem Hauptcampus.\nEbene: *{floor}*"


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
        if not isinstance(item, dict): continue
        name = item.get("name", item.get("title", ""))
        start = item.get("start", item.get("startDate", ""))
        end = item.get("end", item.get("endDate", ""))
        if start: start = _fmt_date(start[:10]) if len(start) >= 10 else start
        if end: end = _date.fromisoformat(end[:10]) if len(end) >= 10 else end
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
    "get_lecturer_info":       _fmt_lecturer_info,
    "get_mensa_menu":          _fmt_mensa,
    "get_mensa_meal_details":  _fmt_mensa_details,
    "get_university_calendar": _fmt_calendar,
    "get_campus_map":          _fmt_map,
    "get_departments":         _fmt_list,
    "get_courses_of_study":    _fmt_list,
    "get_all_rooms":           _fmt_list,
}


def format_results(collected: list[tuple[str, dict]], user_message: str) -> str:
    if not collected:
        return "Ich konnte keine Daten abrufen. Bitte versuche es erneut."
    room_calls = [(n, r) for n, r in collected if n == "get_room_timetable"]
    if len(room_calls) > 1:
        return _fmt_room_multi([r for _, r in room_calls])
    data_calls = [(n, r) for n, r in collected if n not in _LOOKUP_TOOLS]
    if data_calls:
        name, result = data_calls[-1]
        fmt = _FORMATTERS.get(name)
        return fmt(result) if fmt else str(result)
    name, result = collected[-1]
    fmt = _FORMATTERS.get(name)
    return fmt(result) if fmt else str(result)
