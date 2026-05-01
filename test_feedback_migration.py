
import asyncio
import os
import json
from src import db

async def test_feedback():
    await db.init()
    data = {
        "user_id": 12345,
        "type": "test",
        "message": "This is a test feedback"
    }
    filename = await db.save_feedback_json(data)
    print(f"Saved to: {filename}")
    
    path = os.path.join("data/feedback", filename)
    with open(path, "r", encoding="utf-8") as f:
        content = json.load(f)
        print(f"Content: {content}")
        assert content["user_id"] == 12345
        assert "timestamp" in content
        assert content["type"] == "test"
    
    # Cleanup
    # os.remove(path)
    print("Test successful")

if __name__ == "__main__":
    asyncio.run(test_feedback())
