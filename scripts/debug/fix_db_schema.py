
import asyncio
import aiosqlite
import os
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

DB_DIR = "data"
STATE_DB = os.path.join(DB_DIR, "state.db")

async def fix_schema():
    if not os.path.exists(STATE_DB):
        log.error(f"Datenbank {STATE_DB} nicht gefunden!")
        return

    async with aiosqlite.connect(STATE_DB) as db:
        log.info("Prüfe Schema der Tabelle 'users'...")
        
        # Spalten die existieren müssen
        required_columns = {
            "has_consented": "INTEGER NOT NULL DEFAULT 0",
            "is_hka_member": "INTEGER NOT NULL DEFAULT 0",
            "pending_message": "TEXT NOT NULL DEFAULT ''",
            "primary_course": "TEXT",
            "pending_intent": "TEXT",
            "missing_entities": "TEXT",
            "banned": "INTEGER NOT NULL DEFAULT 0",
            "custom_rate_limit": "INTEGER NOT NULL DEFAULT -1"
        }

        async with db.execute("PRAGMA table_info(users)") as cur:
            columns = {row[1] for row in await cur.fetchall()}

        for col, definition in required_columns.items():
            if col not in columns:
                log.info(f"Füge Spalte '{col}' hinzu...")
                try:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
                    await db.commit()
                    log.info(f"Spalte '{col}' erfolgreich hinzugefügt.")
                except Exception as e:
                    log.error(f"Fehler beim Hinzufügen von '{col}': {e}")
            else:
                log.info(f"Spalte '{col}' existiert bereits.")

    log.info("Schema-Fix abgeschlossen.")

if __name__ == "__main__":
    asyncio.run(fix_schema())
