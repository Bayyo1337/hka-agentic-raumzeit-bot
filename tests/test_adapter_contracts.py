from datetime import datetime, timezone

import pytest

from src.domain.models import AdapterResponse, SourceStatus, TimetableResult
from src.integrations.contracts import timetable_from_response


def test_adapter_response_updates_source_metadata():
    fetched_at = datetime.now(timezone.utc)
    response = AdapterResponse(
        payload=TimetableResult(fetched_at=fetched_at),
        fetched_at=fetched_at,
        status=SourceStatus.STALE,
    )
    result = timetable_from_response(response)
    assert result.status is SourceStatus.STALE
    assert result.fetched_at == fetched_at


def test_adapter_contract_rejects_wrong_payload():
    response = AdapterResponse(payload={"events": []}, fetched_at=datetime.now(timezone.utc), status=SourceStatus.FRESH)
    with pytest.raises(TypeError):
        timetable_from_response(response)
