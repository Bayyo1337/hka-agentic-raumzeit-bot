"""
SQLite-Persistenz für Bot-Daten.
Datei: data/bot.db (wird automatisch erstellt)
"""

import json
import logging
import os
import aiosqlite
from datetime import date, datetime, timedelta

log = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "logs/bot.db")


async def init() -> None:
    """Erstellt Tabellen falls nicht vorhanden."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS requests (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                ts        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_requests_user ON requests(user_id);

            CREATE TABLE IF NOT EXISTS tokens (
                user_id      INTEGER PRIMARY KEY,
                input_total  INTEGER NOT NULL DEFAULT 0,
                output_total INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS histories (
                chat_id  INTEGER PRIMARY KEY,
                messages TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS course_index (
                full_key      TEXT PRIMARY KEY,
                abbreviation  TEXT NOT NULL,
                semester      INTEGER NOT NULL,
                group_letter  TEXT NOT NULL DEFAULT '',
                discovered_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_course_abbr ON course_index(abbreviation, semester);

            CREATE TABLE IF NOT EXISTS users (
                user_id           INTEGER PRIMARY KEY,
                username          TEXT NOT NULL DEFAULT '',
                first_name        TEXT NOT NULL DEFAULT '',
                banned            INTEGER NOT NULL DEFAULT 0,
                custom_rate_limit INTEGER NOT NULL DEFAULT -1,
                last_seen         TEXT NOT NULL DEFAULT '',
                primary_course    TEXT
            );

            CREATE TABLE IF NOT EXISTS user_plan_cache (
                user_id   INTEGER PRIMARY KEY,
                plan_json TEXT NOT NULL,
                cached_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS test_cases (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT UNIQUE,
                created_at TEXT NOT NULL
            );
        """)
        # Schema-Migration: Falls die Spalten in users fehlen
        try:
            await db.execute("ALTER TABLE users ADD COLUMN banned INTEGER NOT NULL DEFAULT 0")
        except: pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN custom_rate_limit INTEGER NOT NULL DEFAULT -1")
        except: pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN primary_course TEXT")
        except: pass
        
        await db.commit()
    log.info("Datenbank initialisiert: %s", DB_PATH)


# ── Rate Limiting ────────────────────────────────────────────────────────────

async def check_rate_limit(user_id: int, limit: int) -> bool:
    """
    True = Request erlaubt (und wird eingetragen).
    False = Limit überschritten.
    limit=0 → immer erlaubt.
    """
    if limit == 0:
        await _log_request(user_id)
        return True

    cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        # Aktuelle Anzahl in der letzten Stunde
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id=? AND ts>?",
            (user_id, cutoff),
        ) as cur:
            (count,) = await cur.fetchone()

        if count >= limit:
            return False

        await db.execute(
            "INSERT INTO requests (user_id, ts) VALUES (?, ?)",
            (user_id, datetime.now().isoformat()),
        )
        # Alte Einträge aufräumen (älter als 2 Stunden)
        old_cutoff = (datetime.now() - timedelta(hours=2)).isoformat()
        await db.execute("DELETE FROM requests WHERE ts<?", (old_cutoff,))
        await db.commit()
    return True


async def _log_request(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO requests (user_id, ts) VALUES (?, ?)",
            (user_id, datetime.now().isoformat()),
        )
        await db.commit()


async def get_recent_count(user_id: int) -> int:
    cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id=? AND ts>?",
            (user_id, cutoff),
        ) as cur:
            (count,) = await cur.fetchone()
    return count


async def get_total_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id=?",
            (user_id,),
        ) as cur:
            (count,) = await cur.fetchone()
    return count


async def get_oldest_recent_ts(user_id: int) -> datetime | None:
    """Ältester Timestamp in der letzten Stunde (für Reset-Berechnung)."""
    cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT MIN(ts) FROM requests WHERE user_id=? AND ts>?",
            (user_id, cutoff),
        ) as cur:
            row = await cur.fetchone()
    if row and row[0]:
        return datetime.fromisoformat(row[0])
    return None


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT user_id FROM requests") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


# ── Token-Tracking ───────────────────────────────────────────────────────────

async def add_tokens(user_id: int, input_tokens: int, output_tokens: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO tokens (user_id, input_total, output_total)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                input_total  = input_total  + excluded.input_total,
                output_total = output_total + excluded.output_total
        """, (user_id, input_tokens, output_tokens))
        await db.commit()


async def get_tokens(user_id: int) -> tuple[int, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT input_total, output_total FROM tokens WHERE user_id=?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return row if row else (0, 0)


async def get_all_tokens() -> dict[int, tuple[int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, input_total, output_total FROM tokens") as cur:
            rows = await cur.fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


# ── Kurs-Index ───────────────────────────────────────────────────────────────

async def get_course_variants(abbreviation: str, semester: int) -> list[str]:
    """Gibt alle bekannten full_keys für ein Kürzel+Semester zurück, z.B. ['MABB.7', 'MABB.7.A']."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT full_key FROM course_index WHERE abbreviation=? AND semester=? ORDER BY full_key",
            (abbreviation, semester),
        ) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def save_course_index(entries: list[dict]) -> None:
    """Bulk-Upsert für course_index. entries: [{'full_key', 'abbreviation', 'semester', 'group_letter'}]"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany("""
            INSERT INTO course_index (full_key, abbreviation, semester, group_letter, discovered_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(full_key) DO UPDATE SET discovered_at = excluded.discovered_at
        """, [(e["full_key"], e["abbreviation"], e["semester"], e["group_letter"], now) for e in entries])
        await db.commit()


async def course_index_stale(max_age_days: int = 7) -> bool:
    """True wenn der Index leer ist oder der älteste Eintrag älter als max_age_days Tage."""
    cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT MIN(discovered_at) FROM course_index") as cur:
            row = await cur.fetchone()
    if not row or not row[0]:
        return True
    return row[0] < cutoff


async def get_course_index_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM course_index") as cur:
            (count,) = await cur.fetchone()
    return count


# ── Chat-History ─────────────────────────────────────────────────────────────

async def load_history(chat_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT messages FROM histories WHERE chat_id=?",
            (chat_id,),
        ) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else []


async def save_history(chat_id: int, messages: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO histories (chat_id, messages) VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET messages = excluded.messages
        """, (chat_id, json.dumps(messages, ensure_ascii=False)))
        await db.commit()


async def save_feedback_log(chat_id: int, data: dict) -> str:
    """Speichert eine Feedback-JSON-Datei für manuelle Nachbearbeitung."""
    os.makedirs("data/feedback", exist_ok=True)
    path = f"data/feedback/{date.today().isoformat()}_{chat_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


async def clear_history(chat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM histories WHERE chat_id=?", (chat_id,))
        await db.commit()


# ── Nutzerverwaltung ─────────────────────────────────────────────────────────

async def upsert_user(user_id: int, username: str, first_name: str) -> None:
    """Legt Nutzerdaten an oder aktualisiert sie (bei jeder Nachricht)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_seen  = excluded.last_seen
        """, (user_id, username or "", first_name or "", datetime.now().isoformat()))
        await db.commit()


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, first_name, banned, custom_rate_limit, last_seen "
            "FROM users ORDER BY last_seen DESC"
        ) as cur:
            rows = await cur.fetchall()
    return [
        {"user_id": r[0], "username": r[1], "first_name": r[2],
         "banned": bool(r[3]), "custom_rate_limit": r[4], "last_seen": r[5]}
        for r in rows
    ]


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, first_name, banned, custom_rate_limit, last_seen "
            "FROM users WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return {"user_id": row[0], "username": row[1], "first_name": row[2],
            "banned": bool(row[3]), "custom_rate_limit": row[4], "last_seen": row[5]}


async def find_user_by_username(username: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, first_name, banned, custom_rate_limit, last_seen "
            "FROM users WHERE LOWER(username)=LOWER(?)", (username.lstrip("@"),)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return {"user_id": row[0], "username": row[1], "first_name": row[2],
            "banned": bool(row[3]), "custom_rate_limit": row[4], "last_seen": row[5]}


async def set_banned(user_id: int, banned: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET banned=? WHERE user_id=?", (int(banned), user_id))
        await db.commit()


async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT banned FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return bool(row[0]) if row else False


async def set_custom_rate_limit(user_id: int, limit: int) -> None:
    """-1 = globale Einstellung nutzen."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET custom_rate_limit=? WHERE user_id=?", (limit, user_id)
        )
        await db.commit()


async def set_primary_course(user_id: int, course: str | None) -> None:
    """Setzt den Haupt-Kurs für einen Nutzer (z.B. MABB.7)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET primary_course=? WHERE user_id=?", (course.upper() if course else None, user_id)
        )
        await db.commit()


async def set_primary_courses(user_id: int, courses: list[str]) -> None:
    """Setzt mehrere Kurse als JSON-Liste."""
    val = json.dumps(courses) if courses else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET primary_course=? WHERE user_id=?", (val, user_id)
        )
        await db.commit()


async def add_primary_course(user_id: int, course: str) -> None:
    """Fügt einen Kurs zur Liste hinzu (verhindert Duplikate)."""
    u = await get_user(user_id)
    raw = u.get("primary_course") if u else None
    try:
        courses = json.loads(raw) if raw else []
        if not isinstance(courses, list): courses = [str(raw)]
    except:
        courses = [raw] if raw else []
    
    if course.upper() not in [c.upper() for c in courses]:
        courses.append(course.upper())
        await set_primary_courses(user_id, courses)


async def get_user_plan_cache(user_id: int, max_age_hours: int = 4) -> dict | None:
    """Gibt den Plan aus dem Cache zurück, wenn er nicht zu alt ist."""
    cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT plan_json FROM user_plan_cache WHERE user_id=? AND cached_at>?",
            (user_id, cutoff),
        ) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else None


async def save_user_plan_cache(user_id: int, plan_data: dict) -> None:
    """Speichert einen Plan im Cache."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_plan_cache (user_id, plan_json, cached_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan_json = excluded.plan_json,
                cached_at = excluded.cached_at
        """, (user_id, json.dumps(plan_data, ensure_ascii=False), now))
        await db.commit()


async def get_custom_rate_limit(user_id: int) -> int:
    """-1 = kein Override (globale Einstellung nutzen)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT custom_rate_limit FROM users WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else -1


async def reset_user_requests(user_id: int) -> None:
    """Löscht alle Rate-Limit-Einträge für diesen Nutzer (setzt Zähler zurück)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM requests WHERE user_id=?", (user_id,))
        await db.commit()


async def clear_user_tokens(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tokens WHERE user_id=?", (user_id,))
        await db.commit()


# ── Kurs-Index Extras ─────────────────────────────────────────────────────────

async def get_course_index_age() -> datetime | None:
    """Zeitpunkt des letzten Index-Aufbaus."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT MAX(discovered_at) FROM course_index") as cur:
            row = await cur.fetchone()
    if row and row[0]:
        return datetime.fromisoformat(row[0])
    return None


async def get_course_keys_for_abbr(abbreviation: str) -> list[str]:
    """Alle bekannten Keys für ein Kürzel, z.B. 'MABB' → ['MABB.6', 'MABB.6.A', ...]"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT full_key FROM course_index WHERE abbreviation=? ORDER BY semester, group_letter",
            (abbreviation.upper(),)
        ) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


# ── Feedback-Logs ─────────────────────────────────────────────────────────────

def list_feedback_logs() -> list[str]:
    """Gibt Dateinamen aller Feedback-Logs zurück."""
    path = "data/feedback"
    if not os.path.isdir(path):
        return []
    return sorted(f for f in os.listdir(path) if f.endswith(".json"))


def delete_feedback_log(filename: str) -> bool:
    """Löscht eine einzelne Feedback-Datei. Gibt False zurück wenn nicht gefunden."""
    path = os.path.join("data/feedback", os.path.basename(filename))
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


# ── Stresstest / Regressionstests ────────────────────────────────────────────

async def save_test_case(query: str) -> bool:
    """Speichert eine Test-Anfrage, falls sie noch nicht existiert."""
    now = datetime.now().isoformat()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO test_cases (query_text, created_at) VALUES (?, ?)",
                (query, now)
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False # Duplikat


async def get_all_test_cases() -> list[str]:
    """Gibt alle gespeicherten Test-Anfragen zurück."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT query_text FROM test_cases ORDER BY id DESC") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]
