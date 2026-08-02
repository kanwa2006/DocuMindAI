"""Regression guard for final_audit S2.

Two CPU-bound model inferences ran synchronously from `async def` functions on
the query path:

  • `retrieval_service.py` — the bge-m3 query embedding
  • `grounding_service.py` — the cross-encoder rerank of up to 30 candidates
    at 512 tokens each, which is the dominant CPU cost of a query

Both run on EVERY query — `/ask` as well as `/stream`, not only streaming ones
— so the API serialized all work onto one thread. `llm_service.get_embedding`
already demonstrated the correct pattern; it simply had not been applied here.

Each test drives the real function with a deliberately slow stand-in for the
model and asserts that an independent heartbeat coroutine keeps making
progress. That measures the property that matters (the loop stays free) rather
than asserting on the presence of a `run_in_executor` call, which could be
present and still wrap the wrong thing — the mistake S1 was made of.
"""
import asyncio
import time
import uuid

import pytest

from app.services.grounding_service import GroundingService
from app.services.retrieval_service import RetrievalService

BLOCK_S = 0.5


class _HeartbeatMonitor:
    """Counts how many times the event loop got a turn."""

    def __init__(self):
        self.ticks = 0
        self._stop = False
        self._task = None

    async def __aenter__(self):
        async def beat():
            while not self._stop:
                self.ticks += 1
                await asyncio.sleep(0.01)

        self._task = asyncio.create_task(beat())
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, *exc):
        self._stop = True
        await self._task

    def assert_loop_stayed_free(self, what: str):
        expected = BLOCK_S / 0.01
        assert self.ticks > expected * 0.3, (
            f"only {self.ticks} heartbeats while {what} blocked for {BLOCK_S}s. "
            "The event loop was starved, so this CPU-bound call is running on "
            "the loop thread instead of in an executor (S2)."
        )


class _FakeResult:
    def all(self):
        return []


class _FakeDB:
    async def execute(self, stmt):
        return _FakeResult()


@pytest.mark.asyncio
async def test_query_embedding_does_not_block_the_loop(monkeypatch):
    def slow_embed(texts):
        time.sleep(BLOCK_S)
        return [[0.0] * 1024]

    monkeypatch.setattr(
        "app.services.embedding_service.embedding_service.generate_embeddings",
        slow_embed,
    )

    async with _HeartbeatMonitor() as hb:
        await RetrievalService.retrieve_chunks(
            db=_FakeDB(), query="anything", owner_id=uuid.uuid4()
        )

    hb.assert_loop_stayed_free("the bge-m3 query embedding")


@pytest.mark.asyncio
async def test_reranking_does_not_block_the_loop(monkeypatch):
    def slow_rerank(query, candidates):
        time.sleep(BLOCK_S)
        return []

    monkeypatch.setattr(
        "app.services.reranker_service.reranker_service.rerank_results",
        slow_rerank,
    )
    # Keep retrieval itself instant so only the rerank is under test.
    monkeypatch.setattr(
        "app.services.retrieval_service.RetrievalService.retrieve_chunks",
        _instant_retrieval,
    )

    async with _HeartbeatMonitor() as hb:
        await GroundingService.prepare_grounded_context(
            db=_FakeDB(), query="anything", owner_id=uuid.uuid4()
        )

    hb.assert_loop_stayed_free("the cross-encoder rerank")


async def _instant_retrieval(**kwargs):
    return {
        "query": kwargs.get("query", ""),
        "results": [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "filename": "f.pdf",
                "page_number": 1,
                "chunk_index": 0,
                "text_content": "text",
                "similarity_score": 0.5,
                "lexical_score": 0.5,
                "rrf_score": 0.01,
                "layout_metadata": None,
            }
        ],
        "tracing": {
            "embedding_time_sec": 0.0,
            "database_time_sec": 0.0,
            "total_time_sec": 0.0,
        },
    }
