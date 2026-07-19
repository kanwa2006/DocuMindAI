"""Regression tests for DEBUG_MASTER_PLAN M-1.

The five workspace `/events/*` SSE endpoints emitted fabricated
`progress: i*10` heartbeats disconnected from any task state. They now
stream real persisted state via app/services/processing_events.py:
Document.status transitions (legal/finance/study/research) and JobMatch
counts (HR).
"""
import json
import uuid
from collections import deque
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import processing_events
from app.models.document import DocumentStatus


class _FakeSessionFactory:
    """Callable standing in for AsyncSessionLocal; yields one scripted
    result per poll (the last result repeats)."""

    def __init__(self, results):
        self._results = deque(results)

    def __call__(self):
        value = self._results.popleft() if len(self._results) > 1 else self._results[0]

        class _Session:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *args):
                return False

            async def execute(self_inner, stmt):
                result = MagicMock()
                result.scalar_one_or_none.return_value = value
                result.scalar.return_value = value
                return result

        return _Session()


def _frames(raw_frames):
    return [json.loads(f.split("data: ", 1)[1]) for f in raw_frames]


@pytest.mark.asyncio
async def test_document_stream_follows_real_status_transitions():
    doc_id, owner = uuid.uuid4(), uuid.uuid4()
    docs = [
        SimpleNamespace(status=DocumentStatus.PROCESSING),
        SimpleNamespace(status=DocumentStatus.EXTRACTED),
        SimpleNamespace(status=DocumentStatus.READY),
    ]
    with patch.object(processing_events, "AsyncSessionLocal", _FakeSessionFactory(docs)), \
         patch.object(processing_events.asyncio, "sleep", new=AsyncMock()):
        frames = _frames([
            f async for f in processing_events.document_status_event_stream(doc_id, owner)
        ])

    assert [f["status"] for f in frames] == ["processing", "processing", "complete"]
    assert frames[0]["stage"] == "processing" and frames[0]["progress"] == 50
    assert frames[1]["stage"] == "extracted" and frames[1]["progress"] == 80
    assert frames[2]["progress"] == 100
    assert all(f["document_id"] == str(doc_id) for f in frames)


@pytest.mark.asyncio
async def test_document_stream_reports_failure():
    doc_id, owner = uuid.uuid4(), uuid.uuid4()
    docs = [SimpleNamespace(status=DocumentStatus.FAILED)]
    with patch.object(processing_events, "AsyncSessionLocal", _FakeSessionFactory(docs)), \
         patch.object(processing_events.asyncio, "sleep", new=AsyncMock()):
        frames = _frames([
            f async for f in processing_events.document_status_event_stream(doc_id, owner)
        ])
    assert frames == [{"status": "failed", "document_id": str(doc_id)}]


@pytest.mark.asyncio
async def test_document_stream_not_found():
    doc_id, owner = uuid.uuid4(), uuid.uuid4()
    with patch.object(processing_events, "AsyncSessionLocal", _FakeSessionFactory([None])), \
         patch.object(processing_events.asyncio, "sleep", new=AsyncMock()):
        frames = _frames([
            f async for f in processing_events.document_status_event_stream(doc_id, owner)
        ])
    assert frames == [{"status": "not_found", "document_id": str(doc_id)}]


@pytest.mark.asyncio
async def test_hr_stream_completes_when_candidate_count_stabilizes():
    job_id, workspace = uuid.uuid4(), uuid.uuid4()
    counts = [0, 2, 2, 2, 2]
    with patch.object(processing_events, "AsyncSessionLocal", _FakeSessionFactory(counts)), \
         patch.object(processing_events.asyncio, "sleep", new=AsyncMock()):
        frames = _frames([
            f async for f in processing_events.hr_job_candidates_event_stream(job_id, workspace)
        ])

    assert frames[0] == {"status": "processing", "candidates_processed": 0,
                         "job_id": str(job_id)}
    assert frames[1]["candidates_processed"] == 2
    assert frames[-1] == {"status": "complete", "candidates_processed": 2,
                          "job_id": str(job_id)}
