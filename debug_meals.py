import asyncio, json
from datetime import date
from src import db

async def main():
    await db.init()
    today_str = date.today().isoformat()
    meals = await db.get_mensa_meals_for_day(today_str)
    print(json.dumps(meals, indent=2))

asyncio.run(main())
