import asyncio
import logging
from datetime import date, timedelta
from src import tools as raumzeit

log = logging.getLogger("src.conflicts")

def _parse_time(time_str: str) -> int:
    """Wandelt 'HH:MM' in Minuten seit Mitternacht um."""
    try:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    except:
        return 0

async def find_timetable_conflicts(course_abbr: str, base_sem: int, target_sem: int, module_filter: str | None = None) -> dict:
    """
    Sucht nach Überschneidungen zwischen zwei Semestern eines Studiengangs.
    Berücksichtigt dabei alle Gruppen-Suffixe (.A, .B, .E etc.).
    """
    # 1. Zeitraum festlegen (aktuelle Woche Mo-Fr)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    dates_to_check = [(start_of_week + timedelta(days=i)).isoformat() for i in range(5)]
    
    log.info(f"Suche Konflikte für {course_abbr}: Sem {base_sem} vs {target_sem} (Filter: {module_filter})")

    # 2. Alle Daten sammeln
    # Wir nutzen brute_force, um wirklich alle Gruppen zu erwischen
    base_key = f"{course_abbr}.{base_sem}"
    target_key = f"{course_abbr}.{target_sem}"
    
    base_events = []
    target_events = []

    # Parallelisierung der Abfragen pro Tag
    async def fetch_day(d):
        b_res = await raumzeit.fetch_course_brute_force(base_key, d)
        t_res = await raumzeit.fetch_course_brute_force(target_key, d)
        b = b_res.get("bookings", [])
        t = t_res.get("bookings", [])
        for e in b: e['date'] = d
        for e in t: e['date'] = d
        return b, t

    results = await asyncio.gather(*[fetch_day(d) for d in dates_to_check])
    for b_list, t_list in results:
        base_events.extend(b_list)
        target_events.extend(t_list)

    # 3. Filtern der Basis-Events (falls gewünscht)
    if module_filter:
        f = module_filter.lower()
        base_events = [
            e for e in base_events 
            if f in (e.get("name") or "").lower() or f in (e.get("module") or "").lower()
        ]

    if not base_events:
        return {
            "course": course_abbr,
            "base_sem": base_sem,
            "target_sem": target_sem,
            "filter": module_filter,
            "conflicts": [],
            "error": "Keine Vorlesungen für das Basis-Semester gefunden."
        }

    # 4. Kollisions-Prüfung
    # Wir gruppieren Konflikte nach dem Basis-Event (z.B. nach dem E-Technik Termin)
    conflicts_found = []
    
    # Hilfsfunktion für Overlap
    def overlaps(e1, e2):
        if e1['date'] != e2['date']: return False
        
        # Zeit-Extraktion (falls ISO-String)
        s1_str = e1['start'].split('T')[1][:5] if 'T' in e1['start'] else e1['start']
        e1_t_str = e1['end'].split('T')[1][:5] if 'T' in e1['end'] else e1['end']
        s2_str = e2['start'].split('T')[1][:5] if 'T' in e2['start'] else e2['start']
        e2_t_str = e2['end'].split('T')[1][:5] if 'T' in e2['end'] else e2['end']
        
        s1, e1_t = _parse_time(s1_str), _parse_time(e1_t_str)
        s2, e2_t = _parse_time(s2_str), _parse_time(e2_t_str)
        return s1 < e2_t and s2 < e1_t

    for b_ev in base_events:
        # Saubere Zeiten für die Anzeige
        b_ev["start_clean"] = b_ev['start'].split('T')[1][:5] if 'T' in b_ev['start'] else b_ev['start']
        b_ev["end_clean"] = b_ev['end'].split('T')[1][:5] if 'T' in b_ev['end'] else b_ev['end']
        
        colliding_with = []
        for t_ev in target_events:
            if overlaps(b_ev, t_ev):
                t_ev["start_clean"] = t_ev['start'].split('T')[1][:5] if 'T' in t_ev['start'] else t_ev['start']
                t_ev["end_clean"] = t_ev['end'].split('T')[1][:5] if 'T' in t_ev['end'] else t_ev['end']
                colliding_with.append(t_ev)
        
        conflicts_found.append({
            "base_event": b_ev,
            "conflicts": colliding_with
        })

    return {
        "course": course_abbr,
        "base_sem": base_sem,
        "target_sem": target_sem,
        "filter": module_filter,
        "results": conflicts_found
    }
