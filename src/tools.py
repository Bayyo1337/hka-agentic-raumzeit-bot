"""
Raumzeit API wrapper + Tool-Definitionen im OpenAI-Format (LiteLLM-kompatibel).
Base URL: https://raumzeit.hka-iwi.de
Auth: Bearer JWT via POST /private/api/v1/authentication
"""

import asyncio
import base64
import json
import logging
import os
import re
import time
import unicodedata
from datetime import date as _date, datetime as _datetime
import httpx
from src.config import settings
from src import db

log = logging.getLogger(__name__)

_WEEKDAYS = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}

# ── Dozenten-Namens-Lookup ────────────────────────────────────────────────────

_LECTURERS: dict[str, dict] = {}  # kürzel → {name, email}
_LECTURERS_BY_NAME: dict[str, str] = {}  # normierter name → kürzel

_LECTURERS_PATH = os.environ.get("LECTURERS_PATH", "data/lecturers.json")


def _norm(s: str) -> str:
    s = s.lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def load_lecturers() -> int:
    """Lädt data/lecturers.json. Gibt Anzahl der Einträge zurück (0 wenn nicht vorhanden)."""
    global _LECTURERS, _LECTURERS_BY_NAME
    try:
        with open(_LECTURERS_PATH, encoding="utf-8") as f:
            _LECTURERS = json.load(f)
    except FileNotFoundError:
        return 0
    _LECTURERS_BY_NAME = {}
    for kuerzel, info in _LECTURERS.items():
        name = info.get("name", "")
        # Index: vollständiger normierter Name + jedes einzelne Wort
        _LECTURERS_BY_NAME[_norm(name)] = kuerzel
        for part in name.split():
            _LECTURERS_BY_NAME.setdefault(_norm(part), kuerzel)
    log.info("Dozenten-Index geladen: %d Einträge", len(_LECTURERS))
    return len(_LECTURERS)


def lecturers_stale(max_age_days: int = 7) -> bool:
    """True wenn lecturers.json fehlt oder älter als max_age_days Tage."""
    try:
        mtime = os.path.getmtime(_LECTURERS_PATH)
        return (time.time() - mtime) > max_age_days * 86400
    except FileNotFoundError:
        return True


async def build_lecturer_index() -> int:
    """
    Baut den Dozenten-Index neu auf:
    1. Kürzel aus Kursen UND allen Raum-Belegungen sammeln
    2. HKA-Personenliste scrapen
    3. Matchen, speichern, neu laden
    Gibt Anzahl gematchter Einträge zurück.
    """
    def _norm2ch(s: str) -> str:
        return _norm(s)[:2]

    token = await _get_token()
    known: set[str] = set()

    # 1a. Kürzel aus Kursen
    async with httpx.AsyncClient(base_url=settings.raumzeit_base_url, timeout=15) as c:
        r = await c.get("/api/v1/coursesofstudy/public")
        r.raise_for_status()
        abbreviations = [item["name"] for item in r.json() if isinstance(item, dict) and item.get("name")]

    async def _fetch_course_contacts(key: str):
        try:
            async with httpx.AsyncClient(base_url=settings.raumzeit_base_url, timeout=15) as c:
                r = await c.get(
                    f"/api/v1/timetables/coursesemester/{key}",
                    headers={"Authorization": f"Bearer {token}", "Accept": "text/calendar"},
                )
            if r.status_code == 200:
                for line in r.text.splitlines():
                    if line.startswith("CONTACT:"):
                        for v in line[8:].split(","):
                            if (v := v.strip()): known.add(v)
        except Exception: pass

    # 1b. Kürzel aus ALLEN Räumen (sehr effektiv!)
    rooms = await _get_rooms_cached()
    
    async def _fetch_room_lecturers(room_name: str):
        try:
            async with httpx.AsyncClient(
                base_url=settings.raumzeit_base_url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=15
            ) as c:
                r = await c.get(f"/api/v1/timetables/room/{room_name}")
            if r.status_code == 200:
                data = r.json()
                for entry in (data if isinstance(data, list) else []):
                    for k in (entry.get("lecturers") or []):
                        known.add(k)
        except Exception: pass

    log.info("Dozenten-Index: Sammle Kürzel aus Kursen und Räumen...")
    # Kurse scannen
    keys = [f"{a}.{s}" for a in abbreviations for s in range(1, 8)]
    for i in range(0, len(keys), 40):
        await asyncio.gather(*[_fetch_course_contacts(k) for k in keys[i:i + 40]])
    
    # Alle Räume scannen (Batch)
    room_names = [r.get("name") for r in rooms if isinstance(r, dict) and r.get("name")]
    for i in range(0, len(room_names), 40):
        await asyncio.gather(*[_fetch_room_lecturers(n) for n in room_names[i:i + 40]])
    
    log.info("Dozenten-Index: %d eindeutige Kürzel aus Raumzeit gesammelt", len(known))

    # 2. HKA-Personenliste scrapen
    HKA_BASE = "https://www.h-ka.de"
    persons: list[dict] = []  # [{name, email, url}]
    page = 1
    async with httpx.AsyncClient(base_url=HKA_BASE, timeout=20, follow_redirects=True) as c:
        while True:
            url = f"/die-hochschule-karlsruhe/organisation-personen/personen-a-z?tx_solr%5Bpage%5D={page}"
            try:
                r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
            except Exception: break
            if r.status_code != 200: break
            
            import re as _re
            # Wir suchen nach den Zeilen-Blöcken (TR), um URL, Name und Email zusammenhängend zu finden
            # Pattern für TR mit data-document-url
            tr_pattern = r'<tr[^>]*data-document-url="(.*?)"[^>]*>.*?<span class="person__user-academic-title">(.*?)</span>.*?([\w.\-]+)<span[^>]*>spam prevention</span>@h-ka\.de'
            for p_url, p_name, p_mail_user in _re.findall(tr_pattern, r.text, _re.DOTALL):
                name = _re.sub(r'\s+', ' ', p_name).strip()
                persons.append({
                    "name": name,
                    "vorname": p_mail_user.split(".")[0],
                    "nachname": p_mail_user.split(".")[-1],
                    "email": f"{p_mail_user}@h-ka.de",
                    "url": p_url
                })
            
            if f"page={page + 1}" not in r.text and f"page%5D={page + 1}" not in r.text:
                break
            page += 1
    log.info("Dozenten-Index: %d Personen von h-ka.de geladen", len(persons))

    # 3. Matchen & Sprechzeiten scrapen
    matched: dict[str, dict] = {}
    to_scrape: list[tuple[str, str]] = [] # [(kuerzel, url)]

    for p in persons:
        prefix = _norm2ch(p["nachname"]) + _norm2ch(p["vorname"])
        alt_prefix = _norm(p["nachname"])[:4]
        
        for num in range(1, 21):
            found = False
            for pre in [prefix, alt_prefix]:
                kuerzel = f"{pre}{num:04d}"
                if kuerzel in known:
                    matched[kuerzel] = {"name": p["name"], "email": p["email"]}
                    if p.get("url"):
                        to_scrape.append((kuerzel, p["url"]))
                    found = True
                    break
            if found: break

    # Sprechzeiten asynchron laden (mit Batching um Server zu schonen)
    if to_scrape:
        log.info("Dozenten-Index: Scrape Sprechzeiten für %d Dozenten...", len(to_scrape))
        async def _fetch_sprechzeit(kuerzel: str, profile_url: str):
            try:
                async with httpx.AsyncClient(base_url=HKA_BASE, timeout=10) as c:
                    r = await c.get(profile_url, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    import re as _re
                    # Suche nach Sprechzeiten-Block (Sprechzeiten: <br/> ...)
                    pattern = r'(?:Sprechzeit(?:en)?|Sprechstunde(?:n)?)\s*:\s*<br\s*/?>\s*(.*?)\s*</p>'
                    match = _re.search(pattern, r.text, _re.DOTALL | _re.IGNORECASE)
                    if match:
                        text = _re.sub(r'<[^>]*>', ' ', match.group(1)).strip()
                        matched[kuerzel]["sprechzeit"] = _re.sub(r'\s+', ' ', text)
            except Exception: pass

        for i in range(0, len(to_scrape), 20):
            await asyncio.gather(*[_fetch_sprechzeit(k, u) for k, u in to_scrape[i:i + 20]])
            await asyncio.sleep(0.5) # Kurze Pause zwischen Batches

    # 4. Bestehende manuelle Einträge erhalten
    try:
        with open(_LECTURERS_PATH, encoding="utf-8") as f:
            existing = json.load(f)
            for k, v in existing.items():
                if k not in matched: matched[k] = v
    except FileNotFoundError: pass

    # 5. Speichern + neu laden
    os.makedirs(os.path.dirname(_LECTURERS_PATH), exist_ok=True)
    with open(_LECTURERS_PATH, "w", encoding="utf-8") as f:
        json.dump(matched, f, ensure_ascii=False, indent=2)
    load_lecturers()
    log.info("Dozenten-Index: %d Matches gespeichert", len(matched))
    return len(matched)


def resolve_lecturer(query: str) -> tuple[str, str | None]:
    """
    Löst einen Namen oder ein Kürzel zu (kürzel, vollständiger_name) auf.
    Gibt (query, None) zurück wenn kein Match gefunden.
    Inklusive Fuzzy-Matching für Tippfehler.
    Wendet Namens-Verschönerungen an (Prof./Dozent).
    """
    global _LECTURERS
    if not _LECTURERS:
        load_lecturers()

    def _beautify(name: str) -> str:
        if not name: return name
        # Bereinigen von HTML-Entities falls welche übrig sind
        name = name.replace("&nbsp;", " ").replace("&amp;", "&")
        # Titel prüfen. Falls kein Prof./Dr. vorhanden, als "Dozent" kennzeichnen
        n_lower = name.lower()
        if "prof." not in n_lower and "dozent" not in n_lower:
            return f"Dozent {name}"
        return name

    # 1. Schon ein Kürzel? (z.B. tama0001)
    # Robuste Normalisierung: Alles außer Buchstaben/Zahlen weg
    q_lower = query.lower()
    q_norm = re.sub(r'[^a-z0-9]', '', q_lower)
    
    # Exakter Treffer?
    if re.fullmatch(r"[a-z]{4}\d{4}", q_norm):
        info = _LECTURERS.get(q_norm)
        if not info:
            load_lecturers() # Lazy Load/Refresh
            info = _LECTURERS.get(q_norm)
        
        if info:
            return q_norm, _beautify(info["name"])
    
    # Kürzel irgendwo im String? (z.B. "fedi0001 (Prof. Feßler)")
    match = re.search(r'([a-z]{4}\d{4})', q_lower)
    if match:
        kuerzel = match.group(1)
        info = _LECTURERS.get(kuerzel)
        if not info:
            load_lecturers()
            info = _LECTURERS.get(kuerzel)
            
        if info:
            return kuerzel, _beautify(info["name"])
        log.debug("Dozent-Kürzel %s (aus %s) nicht im Index gefunden", kuerzel, query)

    # 2. Name-Suche: exakt, dann Teilstring
    q = _norm(query)
    if q in _LECTURERS_BY_NAME:
        kuerzel = _LECTURERS_BY_NAME[q]
        return kuerzel, _beautify(_LECTURERS[kuerzel]["name"])

    # 3. Teilstring-Suche über alle normierten Namen
    for norm_name, kuerzel in _LECTURERS_BY_NAME.items():
        if q in norm_name:
            return kuerzel, _beautify(_LECTURERS[kuerzel]["name"])

    # 4. Fuzzy Matching (für Tippfehler wie Peter Offerman -> Offermann)
    import difflib
    matches = difflib.get_close_matches(q, _LECTURERS_BY_NAME.keys(), n=1, cutoff=0.8)
    if matches:
        kuerzel = _LECTURERS_BY_NAME[matches[0]]
        return kuerzel, _beautify(_LECTURERS[kuerzel]["name"])

    return query, None


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
        if not line.strip():
            continue
        log.debug("Parser Raw Line: %s", line)
        parts = line.split("#")
        if len(parts) < 5:
            continue
        try:
            day = int(parts[0])
            if filter_weekday is not None and day != filter_weekday:
                log.debug("Parser Filter: Skip day %d (expected %d)", day, filter_weekday)
                continue
            
            start_min, end_min = int(parts[1]), int(parts[2])
            course_code = parts[3]
            raw_name = parts[4]
            
            # Dozent aus Name extrahieren falls vorhanden (z.B. "Modul (kuer0001)")
            lecturer = ""
            name = raw_name
            import re
            match = re.search(r'\((([a-z]{4}\d{4})|([a-z]{3,10}))\)', raw_name)
            if match:
                kuerzel = match.group(1)
                _, full_name = resolve_lecturer(kuerzel)
                lecturer = full_name or kuerzel
                # Kürzel aus dem Namen entfernen für saubere Darstellung
                name = raw_name.replace(match.group(0), "").strip()
            
            bookings.append({
                "day": _WEEKDAYS.get(day, str(day)),
                "start": f"{start_min // 60:02d}:{start_min % 60:02d}",
                "end": f"{end_min // 60:02d}:{end_min % 60:02d}",
                "course": course_code,
                "name": course_code, # Fallback
                "module": name,
                "lecturer": lecturer
            })
        except (ValueError, IndexError):
            continue
    return bookings

# ---------------------------------------------------------------------------
# Auth & HTTP client
# ---------------------------------------------------------------------------

_token: str | None = None
_token_expires: float = 0.0


def _jwt_expiry(token: str) -> float:
    """Decode JWT exp claim (no signature verification) → monotonic expiry timestamp."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        exp_unix = payload.get("exp", 0)
        return time.monotonic() + (exp_unix - time.time())
    except Exception:
        return time.monotonic() + 3600  # fallback: 1h


async def _get_token() -> str:
    global _token, _token_expires
    if _token and time.monotonic() < _token_expires - 30:
        return _token
    async with httpx.AsyncClient(base_url=settings.raumzeit_base_url) as c:
        r = await c.post(
            "/private/api/v1/authentication",
            json={"login": settings.raumzeit_login, "password": settings.raumzeit_password},
        )
        r.raise_for_status()
        _token = r.json()["accessToken"]
        _token_expires = _jwt_expiry(_token)
        log.debug("Neues JWT geholt, läuft ab in %.0fs", _token_expires - time.monotonic())
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
    rooms = await _get_rooms_cached()
    # Nur relevante Felder zurückgeben — spart Tokens im Formatter/History
    return [{"name": r.get("name", ""), "longName": r.get("longName", "")} 
            for r in rooms if isinstance(r, dict)]


async def get_room_timetable(room_name: str, date: str | None = None) -> dict:
    canonical = await resolve_room_name(room_name)
    token = await _get_token()
    # Datum-Parameter nur für JSON-Endpoints; Text-Format wird client-seitig gefiltert
    params = {"date": date} if date else {}
    async with httpx.AsyncClient(
        base_url=settings.raumzeit_base_url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    ) as c:
        log.debug("API → GET /timetables/room/%s  params=%s", canonical, params)
        r = await c.get(f"/api/v1/timetables/room/{canonical}", params=params)
        if r.status_code == 404:
            return {"error": f"Raum '{canonical}' nicht gefunden. Bitte prüfe den Raumnamen mit get_all_rooms."}
        r.raise_for_status()

    try:
        entries = r.json()
        bookings = []
        # Falls die API trotz Accept-Header Text liefert, wirft r.json() einen Fehler
        if not isinstance(entries, list):
             raise json.JSONDecodeError("Not a list", r.text, 0)
        
        for e in entries:
            if not isinstance(e, dict):
                continue
            
            # Datum prüfen (firstDate ist der Tag des Termins bei WEEKLY/SINGLE)
            occ_date = e.get("firstDate", "")
            if date and occ_date and date != occ_date:
                continue
                
            s_min = e.get("startTime")
            e_min = e.get("endTime")
            course_code = e.get("name", "")
            module_name = e.get("longName", "")
            
            # Ausfallerkennung (JSON)
            is_cancelled = len(e.get("cancellations") or []) > 0
            
            # Dozenten auflösen
            lecturer_list = []
            for kuerzel in (e.get("lecturers") or []):
                _, full_name = resolve_lecturer(kuerzel)
                lecturer_list.append(full_name or kuerzel)
            lecturers_str = ", ".join(lecturer_list)
            
            if isinstance(s_min, int) and isinstance(e_min, int):
                # Format: Minuten seit Mitternacht
                start_str = f"{s_min // 60:02d}:{s_min % 60:02d}"
                end_str = f"{e_min // 60:02d}:{e_min % 60:02d}"
                
                # Wochentag bestimmen
                day_name = ""
                if occ_date:
                    try:
                        dt = _date.fromisoformat(occ_date)
                        day_name = _WEEKDAYS.get(dt.weekday() + 1, "")
                    except ValueError:
                        pass
                
                bookings.append({
                    "name": course_code,
                    "module": module_name,
                    "lecturer": lecturers_str,
                    "start": start_str,
                    "end": end_str,
                    "day": day_name,
                    "date": occ_date,
                    "cancelled": is_cancelled
                })
        log.debug("API ← %d  (%d Belegungen, JSON)", r.status_code, len(bookings))
    except (json.JSONDecodeError, TypeError):
        bookings = _parse_timetable_text(r.text, date)
        if not bookings:
            log.debug("API ← %d (Leeres Ergebnis, roher Text: %s)", r.status_code, r.text[:200])
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
    def _parse_ts(val: str) -> tuple[str, str]:
        """Extrahiert (iso_dt, iso_date) aus iCal-Zeitstempel."""
        val = val.strip().rstrip("Z")
        if ":" in val:
            val = val.split(":")[-1]
        
        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
            try:
                dt = _datetime.strptime(val[:15] if "T" in val else val[:8], fmt)
                return dt.isoformat(), dt.date().isoformat()
            except ValueError:
                continue
        return val, ""

    events = []
    current: dict = {}
    for line in text.splitlines():
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current:
                # Dozent aus SUMMARY extrahieren (z.B. "Modul (fedi0001)")
                raw_name = current.get("name", "")
                name = raw_name
                lecturer = ""
                import re
                match = re.search(r'\((([a-z]{4}\d{4})|([a-z]{3,10}))\)', raw_name)
                if match:
                    kuerzel = match.group(1)
                    _, full_name = resolve_lecturer(kuerzel)
                    lecturer = full_name or kuerzel
                    name = raw_name.replace(match.group(0), "").strip()
                
                current["name"] = name
                current["lecturer"] = lecturer
                events.append(current)
        elif line.startswith("SUMMARY:"):
            current["name"] = line[8:].strip()
        elif line.startswith("DTSTART"):
            val = line.split(":", 1)[-1]
            iso_dt, iso_date = _parse_ts(val)
            current["start"] = iso_dt
            current["date"] = iso_date
        elif line.startswith("DTEND"):
            val = line.split(":", 1)[-1]
            iso_dt, _ = _parse_ts(val)
            current["end"] = iso_dt
        elif line.startswith("LOCATION:"):
            current["room"] = line[9:].strip()

    if filter_date:
        events = [e for e in events if e.get("date") == filter_date]
    elif date_from and date_to:
        events = [e for e in events if date_from <= e.get("date", "") <= date_to]

    return [{
        "name": e.get("name", ""),
        "start": e.get("start", ""),
        "end": e.get("end", ""),
        "room": e.get("room", ""),
        "date": e.get("date", ""),
        "lecturer": e.get("lecturer", ""),
    } for e in events]


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


async def get_lecturer_timetable(account: str, date: str | None = None) -> dict:
    kuerzel, full_name = resolve_lecturer(account)
    if full_name is None and not re.fullmatch(r"[a-z]{4}\d{4}", kuerzel.lower()):
        return {"error": f"Dozent '{account}' nicht gefunden. Bitte Name oder Kürzel (z.B. 'tama0001') angeben. Tipp: /sync ausführen um die Dozenten-Liste zu aktualisieren."}

    info = _LECTURERS.get(kuerzel, {})
    
    token = await _get_token()
    async with _client(token) as c:
        log.debug("API → GET /timetables/lecturer/%s", kuerzel)
        r = await c.get(f"/api/v1/timetables/lecturer/{kuerzel}")
        log.debug("API ← %d  (%d bytes)", r.status_code, len(r.text))
        if r.status_code == 404:
            return {"error": f"Dozent '{account}' nicht gefunden (Kürzel: {kuerzel})."}
        r.raise_for_status()

    bookings = _parse_ical(r.text, filter_date=date)
    return {
        "lecturer": full_name or kuerzel,
        "email": info.get("email"),
        "sprechzeit": info.get("sprechzeit"),
        "bookings": bookings,
        "queried_date": date or "heute"
    }


async def get_lecturer_info(account: str) -> dict:
    """Gibt nur die Kontaktinformationen eines Dozenten zurück."""
    kuerzel, full_name = resolve_lecturer(account)
    if full_name is None:
        return {"error": f"Dozent '{account}' nicht gefunden."}
    
    info = _LECTURERS.get(kuerzel, {})
    return {
        "name": full_name,
        "email": info.get("email"),
        "sprechzeit": info.get("sprechzeit")
    }


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


_probe_sem = asyncio.Semaphore(20)


async def _probe_course_key(key: str) -> bool:
    """Prüft ob ein course_semester-Key in der API existiert (200 = True, sonst False)."""
    async with _probe_sem:
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


async def ping_api() -> dict:
    """Prüft Erreichbarkeit der Raumzeit API: Auth + leichter GET."""
    start = time.monotonic()
    try:
        token = await _get_token()
        auth_ms = int((time.monotonic() - start) * 1000)
        t2 = time.monotonic()
        async with _client(token) as c:
            r = await c.get("/api/v1/departments/public")
        api_ms = int((time.monotonic() - t2) * 1000)
        return {"ok": r.status_code < 400, "auth_ms": auth_ms, "api_ms": api_ms, "status": r.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def get_university_calendar() -> list:
    token = await _get_token()
    async with _client(token) as c:
        r = await c.get("/api/v1/universitycalendar/")
        r.raise_for_status()
        return r.json()


async def get_campus_map(query: str) -> dict:
    """Bestimmt Gebäude und Stockwerk für den Lageplan."""
    query = query.upper().strip()
    building = ""
    floor_info = ""
    
    match = re.match(r"^([A-Z]+)", query)
    if match:
        building = match.group(1)
    
    num_match = re.search(r"(\d+)", query)
    if num_match:
        num = int(num_match.group(1))
        if num >= 100: floor_info = f"{num // 100}. Stock"
        else: floor_info = "Erdgeschoss"
        if "-" in query and query.startswith("-"): floor_info = "Untergeschoss"

    return {
        "action": "send_map",
        "building": building,
        "floor": floor_info,
        "query": query
    }


# ── Mensa-Integration (api.mensa-ka.de) ──────────────────────────────────────

_CANTEENS_CACHE: dict[str, str] = {} # Name/Kürzel -> ID
_MEALS_CACHE: dict[str, dict] = {}    # meal_id -> meal_details

async def _get_canteen_id(query: str | None = None) -> str:
    """Löst einen Mensa-Namen zu einer ID auf. Default: Mensa Moltke."""
    global _CANTEENS_CACHE
    if not _CANTEENS_CACHE:
        try:
            q = "{ getCanteens { id name } }"
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post("https://api.mensa-ka.de", json={"query": q})
                if r.status_code == 200:
                    data = r.json()
                    for c in (data.get("data") or {}).get("getCanteens", []):
                        _CANTEENS_CACHE[_norm(c["name"])] = c["id"]
        except: pass
    
    # Fallback/Default ID für Mensa Moltke
    moltke_id = "8d1af6fc-547e-4078-a7f7-47948304e9fd"
    if not query: return moltke_id
    
    search = _norm(query)
    # Exakter Match oder Teil-Match im Cache suchen
    for name, cid in _CANTEENS_CACHE.items():
        if search in name: return cid
        
    return moltke_id

async def get_mensa_menu(canteen: str | None = None, date: str | None = None) -> dict:
    """Holt den Speiseplan einer Mensa via api.mensa-ka.de (GraphQL)."""
    global _MEALS_CACHE
    if not date:
        date = _date.today().isoformat()
    
    canteen_id = await _get_canteen_id(canteen)
    
    # Neues Schema: getCanteen -> lines -> meals
    query = """
    query GetCanteenMeals($canteenId: ID!, $date: NaiveDate!) {
      getCanteen(canteenId: $canteenId) {
        name
        lines {
          id
          name
          meals(date: $date) {
            id
            name
            price { student employee pupil guest }
            mealType
            allergens
            additives
          }
        }
      }
    }
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.mensa-ka.de",
                json={"query": query, "variables": {"canteenId": canteen_id, "date": date}}
            )
            r.raise_for_status()
            data = r.json()
            
            canteen_data = (data.get("data") or {}).get("getCanteen")
            if not canteen_data:
                return {"canteen": "Mensa", "date": date, "closed": True, "meals": []}
            
            c_name = canteen_data.get("name", "Mensa")
            
            flattened_meals = []
            for line in canteen_data.get("lines", []):
                l_name = line.get("name", "Diverses")
                l_id = line.get("id")
                for m in line.get("meals", []):
                    # Kompatibilität zum Formatter und Fixes
                    m["line"] = {"name": l_name}
                    m["line_id"] = l_id # Für get_mensa_meal_details
                    m["date"] = date
                    
                    # Dietary Flags
                    mtype = m.get("mealType", "UNKNOWN")
                    m["isVegan"] = mtype == "VEGAN"
                    m["isVegetarian"] = mtype in ["VEGAN", "VEGETARIAN"]
                    
                    # Preise von Cent in Euro umrechnen
                    if "price" in m and m["price"]:
                        for k in ["student", "employee", "pupil", "guest"]:
                            if m["price"].get(k):
                                m["price"][k] = m["price"][k] / 100.0
                    
                    flattened_meals.append(m)
                    _MEALS_CACHE[m["id"]] = m
            
            if not flattened_meals:
                 return {"canteen": c_name, "date": date, "closed": True, "meals": []}
            
            return {"canteen": c_name, "date": date, "closed": False, "meals": flattened_meals}
    except Exception as e:
        log.error("Mensa-API Fehler: %s", e)
        return {"error": f"Mensa-API aktuell nicht erreichbar: {e}"}

async def _fetch_canteens_raw():
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.mensa-ka.de", json={"query": "{ getCanteens { id name } }"})
        data = r.json()
        return (data.get("data") or {}).get("getCanteens", [])

async def get_mensa_meal_details(meal_id: str) -> dict:
    """Holt Allergene und Zusatzstoffe für ein spezifisches Gericht."""
    # 1. Aus Cache versuchen
    if meal_id in _MEALS_CACHE:
        return _MEALS_CACHE[meal_id]
        
    # 2. API Fallback (benötigt leider lineId und date im neuen Schema)
    # Da wir diese hier nicht haben, ist der Cache essentiell.
    # Wir könnten versuchen, alle Linien nochmal zu scannen, aber das ist teuer.
    return {"error": "Gerichts-Details aktuell nur direkt nach der Speiseplan-Abfrage verfügbar."}


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
                    "date": {
                        "type": "string",
                        "description": "Datum im Format YYYY-MM-DD (optional).",
                    },
                },
                "required": ["account"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_lecturer_info",
            "description": "Gibt Kontaktinformationen (E-Mail, Sprechzeiten) eines Dozenten zurück.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account": {"type": "string", "description": "Name oder Kürzel des Dozenten."}
                },
                "required": ["account"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_mensa_menu",
            "description": "Gibt den Speiseplan einer Mensa (Default: Moltke) für einen bestimmten Tag zurück.",
            "parameters": {
                "type": "object",
                "properties": {
                    "canteen": {"type": "string", "description": "Name der Mensa (z.B. 'Moltke', 'Adenauerring'). Optional."},
                    "date": {"type": "string", "description": "Datum im Format YYYY-MM-DD (optional)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_mensa_meal_details",
            "description": "Gibt Details (Zusatzstoffe, Allergene) zu einem Gericht zurück.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_id": {"type": "string", "description": "Die technische ID des Gerichts aus get_mensa_menu."}
                },
                "required": ["meal_id"]
            }
        }
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
    {
        "type": "function",
        "function": {
            "name": "get_campus_map",
            "description": "Liefert Informationen zum Ort eines Gebäudes oder Raums auf dem Campus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_or_building": {"type": "string", "description": "Raumname (z.B. LI-145) oder Gebäude (z.B. Gebäude M)."}
                },
                "required": ["room_or_building"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_timetable_conflicts",
            "description": "Analysiert Stundenplan-Überschneidungen zwischen zwei Semestern, optional gefiltert nach einem Fach.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course": {"type": "string", "description": "Name oder Kürzel des Studiengangs (z.B. 'Maschinenbau')."},
                    "base_sem": {"type": "integer", "description": "Das Basis-Semester (z.B. 2)."},
                    "target_sem": {"type": "integer", "description": "Das Ziel-Semester zum Vergleich (z.B. 3)."},
                    "module_filter": {"type": "string", "description": "Optionaler Filter für ein Fach (z.B. 'etechnik')."},
                },
                "required": ["course", "base_sem", "target_sem"],
            },
        },
    }
]

# ---------------------------------------------------------------------------
# Dispatcher: Tool-Name → async Funktion
# ---------------------------------------------------------------------------

TOOL_HANDLERS = {
    "get_all_rooms":           lambda inp: get_all_rooms(),
    "get_room_timetable":      lambda inp: get_room_timetable(inp["room_name"], inp.get("date")),
    "get_course_timetable":    lambda inp: get_course_timetable(inp["course_semester"], inp.get("date")),
    "get_lecturer_timetable":  lambda inp: get_lecturer_timetable(inp["account"], inp.get("date")),
    "get_lecturer_info":       lambda inp: get_lecturer_info(inp["account"]),
    "get_mensa_menu":          lambda inp: get_mensa_menu(inp.get("canteen"), inp.get("date")),
    "get_mensa_meal_details":  lambda inp: get_mensa_meal_details(inp.get("meal_id")),
    "get_departments":         lambda inp: get_departments(),
    "get_courses_of_study":    lambda inp: get_courses_of_study(inp.get("faculty")),
    "get_university_calendar": lambda inp: get_university_calendar(),
    "get_campus_map":          lambda inp: get_campus_map(inp.get("room_or_building", "")),
    "find_timetable_conflicts": lambda inp: _handle_conflicts(inp),
}

async def _handle_conflicts(inp: dict):
    from src.conflicts import find_timetable_conflicts
    # Course-Kürzel auflösen
    course_query = inp.get("course", "")
    _, abbr = await resolve_course_name(course_query)
    if not abbr:
        return {"error": f"Studiengang '{course_query}' konnte nicht zugeordnet werden."}
    
    return await find_timetable_conflicts(
        abbr, 
        int(inp.get("base_sem", 1)), 
        int(inp.get("target_sem", 1)), 
        inp.get("module_filter")
    )
