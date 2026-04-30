import os
import json
import tempfile
import pytest
from pathlib import Path

# Wir setzen DB_DIR auf ein temp directory, um echte DBs nicht zu verändern
# Dies muss VOR dem Import von db/agent passieren.
_TEMP_DB_DIR = tempfile.TemporaryDirectory()
os.environ["DB_DIR"] = _TEMP_DB_DIR.name

from src import db
from src.router import router_instance
from src import agent
from src import tools

fixtures_path = Path(__file__).parent / "fixtures" / "e2e_cases.json"
with open(fixtures_path, "r", encoding="utf-8") as f:
    test_cases = json.load(f)

# Vor dem Ausführen der Tests initialisieren wir die DB
@pytest.fixture(scope="session", autouse=True)
def setup_db_session(request):
    """Cleanup temp dir after all tests."""
    def teardown():
        _TEMP_DB_DIR.cleanup()
    request.addfinalizer(teardown)

import pytest_asyncio

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await db.init()
    await db.upsert_user(12345, "testuser", "Test User")

@pytest.mark.asyncio
@pytest.mark.parametrize("case", test_cases, ids=lambda c: c["name"])
async def test_e2e_flow(case):
    input_text = case["input"]
    expected_intent = case["expected_intent"]
    expected_tools = case["expected_tools"]
    expected_keywords = case["expected_keywords"]
    forbidden_keywords = case["forbidden_keywords"]
    
    # 1. Router Klassifikation prüfen
    state = {}
    router_res = await router_instance.classify_message(input_text, {"user_id": 12345, "chat_id": 12345}, state)
    assert router_res.intent == expected_intent, f"Erwarteter Intent {expected_intent}, bekam {router_res.intent}"
    
    # 2. Agent Ausführung prüfen
    reply, _, _, collected_results = await agent.run(
        input_text, history=[], user_label="testuser", intent=router_res.intent
    )
    
    # 3. Validierung der Tool-Aufrufe
    called_tools = [res[0] for res in collected_results]
    for tool in expected_tools:
        assert tool in called_tools, f"Erwartetes Tool '{tool}' wurde nicht aufgerufen. Aufgerufen: {called_tools}"
        
    # 4. Validierung der Keywords im Markdown
    lower_reply = reply.lower()
    for kw in expected_keywords:
        assert kw.lower() in lower_reply, f"Erwartetes Keyword '{kw}' fehlt in der Antwort:\n{reply}"
        
    for kw in forbidden_keywords:
        assert kw.lower() not in lower_reply, f"Verbotenes Keyword '{kw}' gefunden in der Antwort:\n{reply}"
