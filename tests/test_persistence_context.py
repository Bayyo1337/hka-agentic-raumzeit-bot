from datetime import datetime, timezone

import pytest

from src.domain.models import ConversationState, Intent
from src.persistence.context import ConversationStateRepository


@pytest.mark.asyncio
async def test_conversation_state_round_trip(tmp_path):
    repository = ConversationStateRepository(str(tmp_path / "state.db"))
    await repository.initialize()
    state = ConversationState(
        chat_id=42,
        intent=Intent.ROOM_TIMETABLE,
        entities={"room": "M-102"},
        expected_entity="day",
        original_message="Wann ist M-102 frei?",
        attempts=1,
        expires_at=datetime.now(timezone.utc),
    )
    await repository.save(state)
    assert await repository.get(42) == state
    await repository.clear(42)
    assert await repository.get(42) is None
