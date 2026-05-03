"""
SQLite-Persistenz für Bot-Daten.
Aufgeteilt in 3 Säulen: state.db (User), cache.db (API), telemetry.db (Logs).
"""

import json
import logging
import os
import shutil
import aiosqlite
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

# Pfad-Konfiguration
DB_DIR = os.environ.get("DB_DIR", "data")
OLD_DB_PATH = os.environ.get("DB_PATH", "logs/bot.db") # Für Migration

STATE_DB = os.path.join(DB_DIR, "state.db")
CACHE_DB = os.path.join(DB_DIR, "cache.db")
TELEMETRY_DB = os.path.join(DB_DIR, "telemetry.db")


async def init() -> None:
    """Initialisiert alle 3 Datenbanken und führt Migrationen durch."""
    os.makedirs(DB_DIR, exist_ok=True)

    # 1. Migration von alter bot.db (falls vorhanden)
    if os.path.exists(OLD_DB_PATH) and not os.path.exists(STATE_DB):
        log.info("Migration: Alte Datenbank gefunden (%s). Kopiere nach %s...", OLD_DB_PATH, STATE_DB)
        shutil.copy(OLD_DB_PATH, STATE_DB)
        # Tabellen in state.db bereinigen (Caches/Logs entfernen, da sie in eigene DBs ziehen)
        async with aiosqlite.connect(STATE_DB) as db:
            await db.execute("DROP TABLE IF EXISTS requests")
            await db.execute("DROP TABLE IF EXISTS course_index")
            await db.execute("DROP TABLE IF EXISTS user_plan_cache")
            await db.execute("DROP TABLE IF EXISTS mensa_meals")
            await db.execute("DROP TABLE IF EXISTS test_cases")
            await db.commit()
        log.info("Migration abgeschlossen. Alte Daten wurden in state.db isoliert.")

    # 2. STATE_DB (User, History, Tokens)
    async with aiosqlite.connect(STATE_DB) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id           INTEGER PRIMARY KEY,
                username          TEXT NOT NULL DEFAULT '',
                first_name        TEXT NOT NULL DEFAULT '',
                banned            INTEGER NOT NULL DEFAULT 0,
                custom_rate_limit INTEGER NOT NULL DEFAULT -1,
                last_seen         TEXT NOT NULL DEFAULT '',
                primary_course    TEXT,
                pending_intent    TEXT,
                missing_entities  TEXT,
                has_consented     INTEGER NOT NULL DEFAULT 0,
                pending_message   TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS tokens (
                user_id      INTEGER PRIMARY KEY,
                input_total  INTEGER NOT NULL DEFAULT 0,
                output_total INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS histories (
                chat_id    INTEGER PRIMARY KEY,
                messages   TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS user_privacy_settings (
                user_id               INTEGER PRIMARY KEY,
                allow_profile         INTEGER NOT NULL DEFAULT 1,
                allow_history         INTEGER NOT NULL DEFAULT 1,
                allow_llm             INTEGER NOT NULL DEFAULT 1,
                allow_telemetry       INTEGER NOT NULL DEFAULT 1,
                allow_error_reports   INTEGER NOT NULL DEFAULT 0,
                history_ttl_hours     INTEGER NOT NULL DEFAULT 168,
                telemetry_ttl_hours   INTEGER NOT NULL DEFAULT 24,
                plan_cache_ttl_hours  INTEGER NOT NULL DEFAULT 4,
                feedback_ttl_days     INTEGER NOT NULL DEFAULT 30,
                updated_at            TEXT NOT NULL DEFAULT ''
            );
        """)
        # Migration: Falls Spalten in state.db noch fehlen
        try:
            await db.execute("ALTER TABLE user_privacy_settings ADD COLUMN allow_error_reports INTEGER NOT NULL DEFAULT 0")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed (user_privacy_settings.allow_error_reports): %s", e)
        try:
            await db.execute("ALTER TABLE histories ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed (histories.updated_at): %s", e)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN banned INTEGER NOT NULL DEFAULT 0")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN custom_rate_limit INTEGER NOT NULL DEFAULT -1")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN primary_course TEXT")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN pending_intent TEXT")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN missing_entities TEXT")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN has_consented INTEGER NOT NULL DEFAULT 0")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN pending_message TEXT NOT NULL DEFAULT ''")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                log.error("Migration failed: %s", e)
        await db.commit()

    # 3. CACHE_DB (Kurs-Index, Mensa, Plan-Cache)
    async with aiosqlite.connect(CACHE_DB) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS course_index (
                full_key      TEXT PRIMARY KEY,
                abbreviation  TEXT NOT NULL,
                semester      INTEGER NOT NULL,
                group_letter  TEXT NOT NULL DEFAULT '',
                discovered_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_course_abbr ON course_index(abbreviation, semester);

            CREATE TABLE IF NOT EXISTS user_plan_cache (
                user_id   INTEGER PRIMARY KEY,
                plan_json TEXT NOT NULL,
                cached_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mensa_meals (
                meal_id   TEXT PRIMARY KEY,
                name      TEXT NOT NULL,
                meal_json TEXT NOT NULL,
                date      TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mensa_date ON mensa_meals(date);
            CREATE INDEX IF NOT EXISTS idx_mensa_name ON mensa_meals(name);
        """)
        # Cleanup: Alte Mensa-Einträge löschen (> 14 Tage)
        cutoff = (datetime.now() - timedelta(days=14)).date().isoformat()
        await db.execute("DELETE FROM mensa_meals WHERE date < ?", (cutoff,))
        await db.commit()

    # 4. TELEMETRY_DB (Logs, Tests)
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS requests (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                ts        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_requests_user ON requests(user_id);

            CREATE TABLE IF NOT EXISTS test_cases (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT UNIQUE,
                created_at TEXT NOT NULL
            );
        """)
        await db.commit()

    log.info("Datenbanken initialisiert (Säulen-Modell): %s, %s, %s", STATE_DB, CACHE_DB, TELEMETRY_DB)


# ── Rate Limiting (TELEMETRY_DB) ─────────────────────────────────────────────

async def check_rate_limit(user_id: int, limit: int) -> bool:
    settings = await get_privacy_settings(user_id)
    if not settings.get("allow_telemetry", True):
        return True

    if limit == 0:
        await _log_request(user_id)
        return True

    cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(TELEMETRY_DB) as db:
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
        old_cutoff = (datetime.now() - timedelta(hours=2)).isoformat()
        await db.execute("DELETE FROM requests WHERE ts<?", (old_cutoff,))
        await db.commit()
    return True


async def _log_request(user_id: int) -> None:
    settings = await get_privacy_settings(user_id)
    if not settings.get("allow_telemetry", True):
        return
        
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        await db.execute(
            "INSERT INTO requests (user_id, ts) VALUES (?, ?)",
            (user_id, datetime.now().isoformat()),
        )
        await db.commit()


async def get_recent_count(user_id: int) -> int:
    cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id=? AND ts>?",
            (user_id, cutoff),
        ) as cur:
            (count,) = await cur.fetchone()
    return count


async def get_total_count(user_id: int) -> int:
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id=?",
            (user_id,),
        ) as cur:
            (count,) = await cur.fetchone()
    return count


async def get_oldest_recent_ts(user_id: int) -> datetime | None:
    cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        async with db.execute(
            "SELECT MIN(ts) FROM requests WHERE user_id=? AND ts>?",
            (user_id, cutoff),
        ) as cur:
            row = await cur.fetchone()
    if row and row[0]:
        return datetime.fromisoformat(row[0])
    return None


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        async with db.execute("SELECT DISTINCT user_id FROM requests") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


# ── Token-Tracking (STATE_DB) ────────────────────────────────────────────────

async def add_tokens(user_id: int, input_tokens: int, output_tokens: int) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("""
            INSERT INTO tokens (user_id, input_total, output_total)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                input_total  = input_total  + excluded.input_total,
                output_total = output_total + excluded.output_total
        """, (user_id, input_tokens, output_tokens))
        await db.commit()


async def get_tokens(user_id: int) -> tuple[int, int]:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute(
            "SELECT input_total, output_total FROM tokens WHERE user_id=?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return row if row else (0, 0)


async def get_all_tokens() -> dict[int, tuple[int, int]]:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute("SELECT user_id, input_total, output_total FROM tokens") as cur:
            rows = await cur.fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


async def clear_user_tokens(user_id: int) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("DELETE FROM tokens WHERE user_id=?", (user_id,))
        await db.commit()


async def reset_user_requests(user_id: int) -> None:
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        await db.execute("DELETE FROM requests WHERE user_id=?", (user_id,))
        await db.commit()


# ── Kurs-Index (CACHE_DB) ────────────────────────────────────────────────────

async def get_course_variants(abbreviation: str, semester: int) -> list[str]:
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute(
            "SELECT full_key FROM course_index WHERE abbreviation=? AND semester=? ORDER BY full_key",
            (abbreviation, semester),
        ) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def save_course_index(entries: list[dict]) -> None:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(CACHE_DB) as db:
        await db.executemany("""
            INSERT INTO course_index (full_key, abbreviation, semester, group_letter, discovered_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(full_key) DO UPDATE SET discovered_at = excluded.discovered_at
        """, [(e["full_key"], e["abbreviation"], e["semester"], e["group_letter"], now) for e in entries])
        await db.commit()


async def course_index_stale(max_age_days: int = 7) -> bool:
    cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute("SELECT MIN(discovered_at) FROM course_index") as cur:
            row = await cur.fetchone()
    if not row or not row[0]:
        return True
    return row[0] < cutoff


async def get_course_index_count() -> int:
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute("SELECT COUNT(*) FROM course_index") as cur:
            (count,) = await cur.fetchone()
    return count


# ── Chat-History (STATE_DB) ──────────────────────────────────────────────────

async def load_history(chat_id: int) -> list[dict]:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute(
            "SELECT messages FROM histories WHERE chat_id=?",
            (chat_id,),
        ) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else []


async def save_history(chat_id: int, messages: list[dict]) -> None:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("""
            INSERT INTO histories (chat_id, messages, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET 
                messages = excluded.messages,
                updated_at = excluded.updated_at
        """, (chat_id, json.dumps(messages, ensure_ascii=False), now))
        await db.commit()


async def save_feedback_json(data: dict) -> str:
    """Speichert strukturiertes Feedback als JSON."""
    os.makedirs("data/feedback", exist_ok=True)
    user_id = data.get("user_id", 0)
    # Sanitize type: only alphanumeric
    raw_type = str(data.get("type", "feedback"))
    fb_type = "".join(c for c in raw_type if c.isalnum()) or "feedback"
    
    now = datetime.now()

    # German format for internal JSON
    data["timestamp"] = now.strftime("%d.%m.%Y %H:%M:%S")

    ts_file = now.strftime("%Y-%m-%d_%H%M%S")
    filename = f"{ts_file}_{user_id}_{fb_type}.json"
    path = os.path.join("data/feedback", filename)

    try:
        content = json.dumps(data, ensure_ascii=False, indent=2)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        log.error("Failed to save feedback JSON for user %s: %s", user_id, e)
        # Fallback: Save as plain text if JSON fails
        try:
            with open(path + ".txt", "w", encoding="utf-8") as f:
                f.write(str(data))
            return filename + ".txt"
        except Exception:
            pass
        return ""

    return filename


async def clear_history(chat_id: int) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("DELETE FROM histories WHERE chat_id=?", (chat_id,))
        await db.commit()


# ── Privacy Settings (STATE_DB) ─────────────────────────────────────────────

async def get_privacy_settings(user_id: int) -> dict:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute(
            "SELECT allow_profile, allow_history, allow_llm, allow_telemetry, "
            "history_ttl_hours, telemetry_ttl_hours, plan_cache_ttl_hours, "
            "feedback_ttl_days, allow_error_reports FROM user_privacy_settings WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    
    if not row:
        return {
            "allow_profile": True, "allow_history": True, "allow_llm": True, "allow_telemetry": True,
            "allow_error_reports": False,
            "history_ttl_hours": 168, "telemetry_ttl_hours": 24, "plan_cache_ttl_hours": 4,
            "feedback_ttl_days": 30
        }
    
    return {
        "allow_profile": bool(row[0]), "allow_history": bool(row[1]),
        "allow_llm": bool(row[2]), "allow_telemetry": bool(row[3]),
        "history_ttl_hours": row[4], "telemetry_ttl_hours": row[5],
        "plan_cache_ttl_hours": row[6], "feedback_ttl_days": row[7],
        "allow_error_reports": bool(row[8])
    }


async def set_privacy_settings(user_id: int, settings: dict) -> None:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("""
            INSERT INTO user_privacy_settings (
                user_id, allow_profile, allow_history, allow_llm, allow_telemetry,
                history_ttl_hours, telemetry_ttl_hours, plan_cache_ttl_hours,
                feedback_ttl_days, updated_at, allow_error_reports
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                allow_profile = excluded.allow_profile,
                allow_history = excluded.allow_history,
                allow_llm = excluded.allow_llm,
                allow_telemetry = excluded.allow_telemetry,
                history_ttl_hours = excluded.history_ttl_hours,
                telemetry_ttl_hours = excluded.telemetry_ttl_hours,
                plan_cache_ttl_hours = excluded.plan_cache_ttl_hours,
                feedback_ttl_days = excluded.feedback_ttl_days,
                updated_at = excluded.updated_at,
                allow_error_reports = excluded.allow_error_reports
        """, (
            user_id, int(settings.get("allow_profile", 1)),
            int(settings.get("allow_history", 1)), int(settings.get("allow_llm", 1)),
            int(settings.get("allow_telemetry", 1)), settings.get("history_ttl_hours", 168),
            settings.get("telemetry_ttl_hours", 24), settings.get("plan_cache_ttl_hours", 4),
            settings.get("feedback_ttl_days", 30), now,
            int(settings.get("allow_error_reports", 0))
        ))
        await db.commit()


# ── GDPR Export & Delete ───────────────────────────────────────────────────

async def export_user_data(user_id: int) -> dict:
    data = {"exported_at": datetime.now().isoformat(), "user_id": user_id}
    
    # 1. State DB
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            data["profile"] = await cur.fetchone()
        async with db.execute("SELECT * FROM tokens WHERE user_id=?", (user_id,)) as cur:
            data["tokens"] = await cur.fetchone()
        async with db.execute("SELECT * FROM histories WHERE chat_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            data["history"] = json.loads(row[1]) if row else []
        async with db.execute(
            "SELECT allow_profile, allow_history, allow_llm, allow_telemetry, allow_error_reports, "
            "history_ttl_hours, telemetry_ttl_hours, plan_cache_ttl_hours, feedback_ttl_days, updated_at "
            "FROM user_privacy_settings WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                data["privacy_settings"] = {
                    "allow_profile": bool(row[0]), "allow_history": bool(row[1]),
                    "allow_llm": bool(row[2]), "allow_telemetry": bool(row[3]),
                    "allow_error_reports": bool(row[4]), "history_ttl_hours": row[5],
                    "telemetry_ttl_hours": row[6], "plan_cache_ttl_hours": row[7],
                    "feedback_ttl_days": row[8], "updated_at": row[9]
                }
            else:
                data["privacy_settings"] = None

    # 2. Cache DB
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute("SELECT cached_at, plan_json FROM user_plan_cache WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                data["plan_cache"] = {"cached_at": row[0], "plan": json.loads(row[1])}

    # 3. Telemetry DB
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        async with db.execute("SELECT ts FROM requests WHERE user_id=? ORDER BY ts DESC", (user_id,)) as cur:
            rows = await cur.fetchall()
            data["telemetry"] = {"request_timestamps": [r[0] for r in rows]}

    # 4. Feedback Files
    feedback_dir = "data/feedback"
    data["feedback_files"] = []
    if os.path.isdir(feedback_dir):
        for f in os.listdir(feedback_dir):
            if f.endswith(".json"):
                parts = f.replace(".json", "").split("_")
                if len(parts) >= 3 and parts[2] == str(user_id):
                    try:
                        with open(os.path.join(feedback_dir, f), "r", encoding="utf-8") as j:
                            data["feedback_files"].append({"filename": f, "content": json.load(j)})
                    except Exception as e:
                        log.error("Failed to export feedback file %s: %s", f, e)
    
    return data


async def delete_user_data(user_id: int) -> bool:
    """Hard delete aller personenbezogenen Daten eines Nutzers."""
    # 1. State DB
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM tokens WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM histories WHERE chat_id=?", (user_id,))
        await db.execute("DELETE FROM user_privacy_settings WHERE user_id=?", (user_id,))
        await db.commit()
    
    # 2. Cache DB
    async with aiosqlite.connect(CACHE_DB) as db:
        await db.execute("DELETE FROM user_plan_cache WHERE user_id=?", (user_id,))
        await db.commit()
    
    # 3. Telemetry DB
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        await db.execute("DELETE FROM requests WHERE user_id=?", (user_id,))
        await db.commit()
    
    # 4. Feedback Files
    feedback_dir = "data/feedback"
    if os.path.isdir(feedback_dir):
        for f in os.listdir(feedback_dir):
            if f.endswith(".json"):
                parts = f.replace(".json", "").split("_")
                if len(parts) >= 3 and parts[2] == str(user_id):
                    try:
                        os.remove(os.path.join(feedback_dir, f))
                    except Exception as e:
                        log.error("Failed to delete feedback file %s: %s", f, e)
    
    return True


async def run_gdpr_cleanup() -> dict:
    """Bereinigt abgelaufene Daten basierend auf individuellen TTLs."""
    stats = {"histories": 0, "telemetry": 0, "plan_cache": 0, "feedback": 0}
    now = datetime.now()
    
    # Defaults
    D_HIST, D_TELEM, D_PLAN, D_FEED = 168, 24, 4, 30

    # 1. Custom-Settings abrufen & gruppieren
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute(
            "SELECT user_id, history_ttl_hours, telemetry_ttl_hours, "
            "plan_cache_ttl_hours, feedback_ttl_days FROM user_privacy_settings"
        ) as cur:
            settings_rows = await cur.fetchall()
    
    h_groups, t_groups, p_groups, ttl_map = {}, {}, {}, {}
    custom_uids = []
    for uid, h_ttl, t_ttl, p_ttl, f_ttl in settings_rows:
        h_groups.setdefault(h_ttl, []).append(uid)
        t_groups.setdefault(t_ttl, []).append(uid)
        p_groups.setdefault(p_ttl, []).append(uid)
        ttl_map[uid] = f_ttl
        custom_uids.append(uid)

    # 2. Histories (STATE_DB)
    async with aiosqlite.connect(STATE_DB) as db:
        # Custom TTLs
        for ttl, uids in h_groups.items():
            cutoff = (now - timedelta(hours=ttl)).isoformat()
            for i in range(0, len(uids), 900):
                chunk = uids[i:i+900]
                placeholders = ",".join(["?"] * len(chunk))
                cur = await db.execute(f"DELETE FROM histories WHERE chat_id IN ({placeholders}) AND updated_at < ?", chunk + [cutoff])
                stats["histories"] += cur.rowcount
        
        # Default TTLs (those not in custom_uids)
        cutoff_def = (now - timedelta(hours=D_HIST)).isoformat()
        if custom_uids:
            for i in range(0, len(custom_uids), 900):
                chunk = custom_uids[i:i+900]
                placeholders = ",".join(["?"] * len(chunk))
                cur = await db.execute(f"DELETE FROM histories WHERE updated_at < ? AND chat_id NOT IN ({placeholders})", [cutoff_def] + chunk)
                stats["histories"] += cur.rowcount
        else:
            cur = await db.execute("DELETE FROM histories WHERE updated_at < ?", (cutoff_def,))
            stats["histories"] += cur.rowcount
        await db.commit()

    # 3. Telemetry (TELEMETRY_DB)
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        # Custom TTLs
        for ttl, uids in t_groups.items():
            cutoff = (now - timedelta(hours=ttl)).isoformat()
            for i in range(0, len(uids), 900):
                chunk = uids[i:i+900]
                placeholders = ",".join(["?"] * len(chunk))
                cur = await db.execute(f"DELETE FROM requests WHERE user_id IN ({placeholders}) AND ts < ?", chunk + [cutoff])
                stats["telemetry"] += cur.rowcount
        
        # Default TTLs
        cutoff_def = (now - timedelta(hours=D_TELEM)).isoformat()
        if custom_uids:
            for i in range(0, len(custom_uids), 900):
                chunk = custom_uids[i:i+900]
                placeholders = ",".join(["?"] * len(chunk))
                cur = await db.execute(f"DELETE FROM requests WHERE ts < ? AND user_id NOT IN ({placeholders})", [cutoff_def] + chunk)
                stats["telemetry"] += cur.rowcount
        else:
            cur = await db.execute("DELETE FROM requests WHERE ts < ?", (cutoff_def,))
            stats["telemetry"] += cur.rowcount
        await db.commit()

    # 4. Plan Cache (CACHE_DB)
    async with aiosqlite.connect(CACHE_DB) as db:
        # Custom TTLs
        for ttl, uids in p_groups.items():
            cutoff = (now - timedelta(hours=ttl)).isoformat()
            for i in range(0, len(uids), 900):
                chunk = uids[i:i+900]
                placeholders = ",".join(["?"] * len(chunk))
                cur = await db.execute(f"DELETE FROM user_plan_cache WHERE user_id IN ({placeholders}) AND cached_at < ?", chunk + [cutoff])
                stats["plan_cache"] += cur.rowcount
        
        # Default TTLs
        cutoff_def = (now - timedelta(hours=D_PLAN)).isoformat()
        if custom_uids:
            for i in range(0, len(custom_uids), 900):
                chunk = custom_uids[i:i+900]
                placeholders = ",".join(["?"] * len(chunk))
                cur = await db.execute(f"DELETE FROM user_plan_cache WHERE cached_at < ? AND user_id NOT IN ({placeholders})", [cutoff_def] + chunk)
                stats["plan_cache"] += cur.rowcount
        else:
            cur = await db.execute("DELETE FROM user_plan_cache WHERE cached_at < ?", (cutoff_def,))
            stats["plan_cache"] += cur.rowcount
        await db.commit()

    # 5. Feedback Files
    feedback_dir = "data/feedback"
    if os.path.isdir(feedback_dir):
        for f in os.listdir(feedback_dir):
            if f.endswith(".json"):
                fpath = os.path.join(feedback_dir, f)
                parts = f.replace(".json", "").split("_")
                days = D_FEED
                if len(parts) >= 3:
                    try:
                        uid = int(parts[2])
                        days = ttl_map.get(uid, D_FEED)
                    except (ValueError, TypeError): pass
                
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if (now - mtime).days > days:
                    try:
                        os.remove(fpath)
                        stats["feedback"] += 1
                    except Exception as e:
                        log.error("Failed to cleanup feedback file %s: %s", f, e)
    
    return stats


# ── Nutzerverwaltung (STATE_DB) ──────────────────────────────────────────────

async def get_consent_status(user_id: int) -> int:
    try:
        async with aiosqlite.connect(STATE_DB) as db:
            async with db.execute(
                "SELECT has_consented FROM users WHERE user_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
        return row[0] if row else 0
    except Exception as e:
        log.error("Error in get_consent_status: %s", e)
        return 0

async def _upsert_user_field(user_id: int, field: str, value) -> None:
    if field not in {"has_consented", "pending_message"}:
        raise ValueError(f"Unsupported user field: {field}")
    now = datetime.now().isoformat()
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute(f"""
            INSERT INTO users (user_id, username, first_name, last_seen, {field})
            VALUES (?, '', '', ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                {field} = excluded.{field},
                last_seen = excluded.last_seen
        """, (user_id, now, value))
        await db.commit()

async def set_consent_status(user_id: int, status: int) -> None:
    try:
        await _upsert_user_field(user_id, "has_consented", status)
    except Exception as e:
        log.error("Error in set_consent_status: %s", e)

async def save_pending_message(user_id: int, msg: str) -> None:
    try:
        await _upsert_user_field(user_id, "pending_message", msg)
    except Exception as e:
        log.error("Error in save_pending_message: %s", e)

async def get_and_clear_pending_message(user_id: int) -> str:
    try:
        async with aiosqlite.connect(STATE_DB) as db:
            async with db.execute(
                "SELECT pending_message FROM users WHERE user_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
            
            msg = row[0] if row and row[0] else ""
            if msg:
                await db.execute(
                    "UPDATE users SET pending_message='' WHERE user_id=?", (user_id,)
                )
                await db.commit()
            return msg
    except Exception as e:
        log.error("Error in get_and_clear_pending_message: %s", e)
        return ""

async def upsert_user(user_id: int, username: str, first_name: str) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
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
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute(
            "SELECT user_id, username, first_name, banned, custom_rate_limit, last_seen, pending_intent, missing_entities, primary_course "
            "FROM users ORDER BY last_seen DESC"
        ) as cur:
            rows = await cur.fetchall()
    return [
        {"user_id": r[0], "username": r[1], "first_name": r[2],
         "banned": bool(r[3]), "custom_rate_limit": r[4], "last_seen": r[5],
         "pending_intent": r[6], "missing_entities": r[7], "primary_course": r[8]}
        for r in rows
    ]


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute(
            "SELECT user_id, username, first_name, banned, custom_rate_limit, last_seen, pending_intent, missing_entities, primary_course "
            "FROM users WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return {"user_id": row[0], "username": row[1], "first_name": row[2],
            "banned": bool(row[3]), "custom_rate_limit": row[4], "last_seen": row[5],
            "pending_intent": row[6], "missing_entities": row[7], "primary_course": row[8]}


async def find_user_by_username(username: str) -> dict | None:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute(
            "SELECT user_id, username, first_name, banned, custom_rate_limit, last_seen, pending_intent, missing_entities, primary_course "
            "FROM users WHERE LOWER(username)=LOWER(?)", (username.lstrip("@"),)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return {"user_id": row[0], "username": row[1], "first_name": row[2],
            "banned": bool(row[3]), "custom_rate_limit": row[4], "last_seen": row[5],
            "pending_intent": row[6], "missing_entities": row[7], "primary_course": row[8]}

async def set_intent_state(user_id: int, intent: str | None, missing_entities: dict | None = None) -> None:
    val_intent = intent
    val_entities = json.dumps(missing_entities) if missing_entities is not None else None
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute(
            "UPDATE users SET pending_intent=?, missing_entities=? WHERE user_id=?", 
            (val_intent, val_entities, user_id)
        )
        await db.commit()


async def set_banned(user_id: int, banned: bool) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute("UPDATE users SET banned=? WHERE user_id=?", (int(banned), user_id))
        await db.commit()


async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute("SELECT banned FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return bool(row[0]) if row else False


async def set_custom_rate_limit(user_id: int, limit: int) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute(
            "UPDATE users SET custom_rate_limit=? WHERE user_id=?", (limit, user_id)
        )
        await db.commit()


async def get_custom_rate_limit(user_id: int) -> int:
    """-1 = kein Override (globale Einstellung nutzen)."""
    async with aiosqlite.connect(STATE_DB) as db:
        async with db.execute(
            "SELECT custom_rate_limit FROM users WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else -1


async def set_primary_course(user_id: int, course: str | None) -> None:
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute(
            "UPDATE users SET primary_course=? WHERE user_id=?", (course.upper() if course else None, user_id)
        )
        await db.commit()


async def set_primary_courses(user_id: int, courses: list[str]) -> None:
    val = json.dumps(courses) if courses else None
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute(
            "UPDATE users SET primary_course=? WHERE user_id=?", (val, user_id)
        )
        await db.commit()


async def add_primary_course(user_id: int, course: str) -> None:
    u = await get_user(user_id)
    raw = u.get("primary_course") if u else None
    try:
        courses = json.loads(raw) if raw else []
        if not isinstance(courses, list):
            courses = [str(raw)]
    except Exception:
        courses = [raw] if raw else []
    
    if course.upper() not in [c.upper() for c in courses]:
        courses.append(course.upper())
        await set_primary_courses(user_id, courses)


async def get_user_course_config(user_id: int) -> list[dict]:
    """Returns a list of dicts: [{'key': 'MABB.7', 'excluded_groups': [], 'excluded_modules': []}]"""
    u = await get_user(user_id)
    raw = u.get("primary_course") if u else None
    if not raw: return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list): return []
        # Migrate old list of strings to new dict format
        return [{"key": item, "excluded_groups": [], "excluded_modules": []} if isinstance(item, str) else item for item in data]
    except json.JSONDecodeError:
        # Fallback if it was just a string
        return [{"key": raw, "excluded_groups": [], "excluded_modules": []}]

async def save_user_course_config(user_id: int, config: list[dict]) -> None:
    val = json.dumps(config) if config else None
    async with aiosqlite.connect(STATE_DB) as db:
        await db.execute(
            "UPDATE users SET primary_course=? WHERE user_id=?", (val, user_id)
        )
        await db.commit()

async def add_course_to_config(user_id: int, course_key: str) -> None:
    config = await get_user_course_config(user_id)
    if not any(c["key"].upper() == course_key.upper() for c in config):
        config.append({"key": course_key.upper(), "excluded_groups": [], "excluded_modules": []})
        await save_user_course_config(user_id, config)

async def remove_course_from_config(user_id: int, course_key: str) -> None:
    config = await get_user_course_config(user_id)
    config = [c for c in config if c["key"].upper() != course_key.upper()]
    await save_user_course_config(user_id, config)


# ── Cache-Extras (CACHE_DB) ──────────────────────────────────────────────────

async def get_user_plan_cache(user_id: int, max_age_hours: int = 4) -> dict | None:
    cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute(
            "SELECT plan_json FROM user_plan_cache WHERE user_id=? AND cached_at>?",
            (user_id, cutoff),
        ) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else None


async def save_user_plan_cache(user_id: int, plan_data: dict) -> None:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(CACHE_DB) as db:
        await db.execute("""
            INSERT INTO user_plan_cache (user_id, plan_json, cached_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan_json = excluded.plan_json,
                cached_at = excluded.cached_at
        """, (user_id, json.dumps(plan_data, ensure_ascii=False), now))
        await db.commit()


async def get_course_index_age() -> datetime | None:
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute("SELECT MAX(discovered_at) FROM course_index") as cur:
            row = await cur.fetchone()
    if row and row[0]:
        return datetime.fromisoformat(row[0])
    return None


async def get_course_keys_for_abbr(abbreviation: str) -> list[str]:
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute(
            "SELECT full_key FROM course_index WHERE abbreviation=? ORDER BY semester, group_letter",
            (abbreviation.upper(),)
        ) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


# ── Mensa-Cache (CACHE_DB) ───────────────────────────────────────────────────

async def save_mensa_meals(meals: list[dict]) -> None:
    async with aiosqlite.connect(CACHE_DB) as db:
        await db.executemany("""
            INSERT INTO mensa_meals (meal_id, name, meal_json, date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(meal_id) DO UPDATE SET
                name      = excluded.name,
                meal_json = excluded.meal_json,
                date      = excluded.date
        """, [(m["id"], m["name"], json.dumps(m, ensure_ascii=False), m["date"]) for m in meals])
        await db.commit()


async def get_mensa_meal_by_id(meal_id: str) -> dict | None:
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute(
            "SELECT meal_json FROM mensa_meals WHERE meal_id=?", (meal_id,)
        ) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else None


async def get_all_mensa_meals_for_fuzzy(date: str | None = None) -> dict[str, str]:
    async with aiosqlite.connect(CACHE_DB) as db:
        if date:
            async with db.execute(
                "SELECT name, meal_id FROM mensa_meals WHERE date = ?", (date,)
            ) as cur:
                rows = await cur.fetchall()
        else:
            cutoff = (datetime.now() - timedelta(days=3)).date().isoformat()
            async with db.execute(
                "SELECT name, meal_id FROM mensa_meals WHERE date >= ?", (cutoff,)
            ) as cur:
                rows = await cur.fetchall()
    return {r[0]: r[1] for r in rows}


async def get_mensa_meals_for_day(date_str: str) -> list[dict]:
    """Gibt alle Gerichte eines bestimmten Tages zurück (für Kategorie-Lookup)."""
    async with aiosqlite.connect(CACHE_DB) as db:
        async with db.execute(
            "SELECT meal_json FROM mensa_meals WHERE date=?", (date_str,)
        ) as cur:
            rows = await cur.fetchall()
    return [json.loads(r[0]) for r in rows]


async def clear_mensa_cache() -> None:
    """Löscht alle Mensa-Gerichte aus dem Cache (für Tests)."""
    async with aiosqlite.connect(CACHE_DB) as db:
        await db.execute("DELETE FROM mensa_meals")
        await db.commit()


# ── Telemetrie & Feedback (TELEMETRY_DB) ─────────────────────────────────────

async def save_test_case(query: str) -> bool:
    now = datetime.now().isoformat()
    try:
        async with aiosqlite.connect(TELEMETRY_DB) as db:
            await db.execute(
                "INSERT INTO test_cases (query_text, created_at) VALUES (?, ?)",
                (query, now)
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def get_all_test_cases() -> list[str]:
    async with aiosqlite.connect(TELEMETRY_DB) as db:
        async with db.execute("SELECT query_text FROM test_cases ORDER BY id DESC") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


def list_feedback_logs() -> list[str]:
    path = "data/feedback"
    if not os.path.isdir(path): return []
    return sorted(f for f in os.listdir(path) if f.endswith(".json"))


def delete_feedback_log(filename: str) -> bool:
    path = os.path.join("data/feedback", os.path.basename(filename))
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False
