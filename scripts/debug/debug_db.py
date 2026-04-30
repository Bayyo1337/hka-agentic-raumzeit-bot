import asyncio
import aiosqlite
import os

async def main():
    if os.path.exists("data/state.db"):
        print("state.db exists")
    
    async with aiosqlite.connect("data/state.db") as db:
        try:
            await db.execute("ALTER TABLE users ADD COLUMN pending_intent TEXT")
            await db.commit()
            print("Added pending_intent")
        except Exception as e:
            print("Error pending_intent:", e)

asyncio.run(main())
