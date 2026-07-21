"""Regression test for DEBUG_MASTER_PLAN N-1.

The DeepResearchAgent existed but no endpoint or frontend code ever
invoked it. POST /research/deep-research now streams its ResearchEvents
as SSE frames, validating document ownership first.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.research import deep_research, DeepResearchRequest
from app.services.deep_research_agent import ResearchEvent

USER = {"id": str(uuid.uuid4()), "workspace_id": "research"}


@pytest.mark.asyncio
async def test_deep_research_streams_agent_events():
    async def fake_research(query, doc_ids, session_id=None, db=None):
        yield ResearchEvent(step=1, status="running", message="Analyzing...")
        yield ResearchEvent(step="final", status="complete", answer="done answer")

    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None  # no owned docs match
    db.execute = AsyncMock(return_value=result)

    with patch(
        "app.services.deep_research_agent.deep_research_agent.research",
        side_effect=fake_research,
    ) as mock_research:
        response = await deep_research(
            DeepResearchRequest(query="q", doc_ids=[str(uuid.uuid4())]), USER, db
        )
        frames = [chunk async for chunk in response.body_iterator]

    # Unowned doc ids are filtered out before the agent runs.
    args, kwargs = mock_research.call_args
    assert args[1] == []

    payloads = [
        json.loads(f.replace("data: ", "").strip())
        for f in frames if f.startswith("data: ") and "[DONE]" not in f
    ]
    assert payloads[0]["step"] == 1
    assert payloads[-1]["status"] == "complete"
    assert frames[-1].strip().endswith("[DONE]")
