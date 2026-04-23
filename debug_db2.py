import asyncio
import aiosqlite
import os

async def main():
    async with aiosqlite.connect("data/state.db") as db:
        try:
            await db.execute("ALTER TABLE users ADD COLUMN missing_entities TEXT")
            await db.commit()
            print("Added missing_entities")
        except Exception as e:
            print("Error missing_entities:", e)

asyncio.run(main())
