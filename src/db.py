"""
SQLite-Persistenz für Bot-Daten.
Datei: data/bot.db (wird automatisch erstellt)
"""

import json
import logging
import os
import aiosqlite
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "data/bot.db")


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
        """)
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


async def clear_history(chat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM histories WHERE chat_id=?", (chat_id,))
        await db.commit()
