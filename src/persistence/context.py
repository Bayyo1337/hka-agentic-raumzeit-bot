import json
from datetime import datetime

import aiosqlite

from src.domain.models import ConversationState, Intent


class ConversationStateRepository:
    """SQLite repository for clarification state, independent of Telegram."""

    def __init__(self, path: str) -> None:
        self.path = path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_states (
                    chat_id INTEGER PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def get(self, chat_id: int) -> ConversationState | None:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT state_json FROM conversation_states WHERE chat_id = ?",
                (chat_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        return ConversationState.model_validate_json(row[0])

    async def save(self, state: ConversationState) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO conversation_states(chat_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (state.chat_id, state.model_dump_json(), datetime.now().isoformat()),
            )
            await db.commit()

    async def clear(self, chat_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM conversation_states WHERE chat_id = ?", (chat_id,))
            await db.commit()


def state_from_json(chat_id: int, raw: str) -> ConversationState:
    data = json.loads(raw)
    data["chat_id"] = chat_id
    if data.get("intent"):
        data["intent"] = Intent(data["intent"])
    return ConversationState.model_validate(data)
